#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["playwright==1.63.0"]
# ///
import argparse
import json
import pathlib
import re
import sys
import tempfile
from urllib.parse import urlparse

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

PROBE = pathlib.Path(__file__).with_name("probe.js").read_text()
INTERACT = pathlib.Path(__file__).with_name("interact.js").read_text()
STRESS = pathlib.Path(__file__).with_name("stress.js").read_text()
STILL = "*,*::before,*::after{animation:none!important;transition:none!important;caret-color:transparent!important}"
STYLE_FIELDS = ["font-size", "font-weight", "font", "color", "background", "radius", "padding", "border", "text-transform", "shadow"]
LAYOUT_FIELDS = ["contentLeft", "contentRight", "headerHeight", "sidebarWidth", "bodyFont", "h1", "radius", "controlHeight", "iconSize"]
CROP_LIMIT = 12
PROPERTIES = {
    "inconsistent": ["font-size", "padding", "height", "min-height", "border-radius", "font-weight"],
    "scale": ["font-size", "border-radius"],
    "drift": ["font-size", "color", "background-color"],
    "small-text": ["font-size"],
    "icon-centre": ["margin-top", "vertical-align", "top", "align-items"],
    "off-centre": ["padding", "padding-top", "padding-bottom", "line-height", "height"],
    "cramped-padding": ["padding"],
    "table-column": ["padding", "padding-left", "padding-right", "text-align"],
    "numeric-align": ["text-align", "font-variant-numeric"],
    "contrast": ["color"],
    "row-height": ["height", "min-height", "padding", "line-height"],
    "gap": ["gap", "margin", "margin-top", "margin-bottom"],
    "edge": ["margin", "margin-left", "padding", "padding-left"],
    "control-cut": ["width", "min-width", "max-width", "flex", "white-space", "overflow"],
    "clipped": ["width", "max-width", "overflow", "white-space", "height"],
    "overflow-x": ["width", "min-width", "white-space"],
    "control-font": ["font", "font-family", "font-size"],
    "proximity": ["margin", "margin-top", "margin-bottom"],
}


def as_url(arg):
    path = pathlib.Path(arg)
    return path.resolve().as_uri() if path.exists() else arg


def slug(url):
    parsed = urlparse(url)
    if parsed.scheme == "file":
        return re.sub(r"[^A-Za-z0-9]+", "-", pathlib.Path(parsed.path).stem)
    name = parsed.path.strip("/") or "index"
    if parsed.netloc:
        name = f"{parsed.netloc}-{name}"
    if parsed.query:
        name = f"{name}-{parsed.query}"
    return re.sub(r"[^A-Za-z0-9]+", "-", name).strip("-")[-60:]


def page_label(url):
    parsed = urlparse(url)
    if parsed.scheme == "file":
        return pathlib.Path(parsed.path).name
    return (parsed.path or "/") + (f"?{parsed.query}" if parsed.query else "")


def load(page, url, width, height=900):
    page.set_viewport_size({"width": width, "height": height})
    page.goto(url, wait_until="load")
    try:
        page.wait_for_load_state("networkidle", timeout=5000)
    except PlaywrightTimeout:
        pass
    page.add_style_tag(content=STILL)
    page.evaluate("document.fonts.ready.then(() => true)")


def interact(page):
    page.mouse.move(-1, -1)
    checks = page.evaluate_handle(INTERACT)
    for _ in range(60):
        before = checks.evaluate_handle("checks => checks.snapshot()")
        page.keyboard.press("Tab")
        more = checks.evaluate("(checks, before) => checks.focus(before)", before)
        before.dispose()
        if not more:
            break
    page.evaluate("document.activeElement?.blur()")
    controls = "button, a[href], input, select, textarea, [role=button], [role=tab], [role=menuitem]"
    count = 0
    for index, control in enumerate(page.query_selector_all(controls)):
        if not control.is_visible():
            continue
        page.mouse.move(-1, -1)
        control.scroll_into_view_if_needed()
        before = checks.evaluate_handle("checks => checks.snapshot()")
        try:
            page.hover(f":is({controls}) >> nth={index}", timeout=2000)
            checks.evaluate("(checks, args) => checks.hover(args[0], args[1])", [control, before])
        except PlaywrightTimeout:
            pass
        finally:
            before.dispose()
        count += 1
        if count >= 40:
            break
    page.mouse.move(-1, -1)
    found = checks.evaluate("checks => checks.findings()")
    checks.dispose()
    found += popups(page)
    merged = {}
    for f in found:
        if f["kind"] in merged:
            m = merged[f["kind"]]
            m["count"] += f["count"]
            m["elements"] = (m["elements"] + f["elements"])[:4]
            m["boxes"] = (m["boxes"] + f["boxes"])[:4]
        else:
            merged[f["kind"]] = dict(f)
    return [{**f, "message": f"{f['message']} ({f.pop('count')} element(s))"} for f in merged.values()]


def popups(page):
    triggers = "[aria-haspopup]:not([aria-haspopup=false]), [aria-expanded=false], summary"
    found = []
    checks = None
    for index in range(15):
        try:
            if checks is None:
                checks = page.evaluate_handle(INTERACT)
            listed = page.query_selector_all(triggers)
            if index >= len(listed):
                break
            if not listed[index].is_visible():
                continue
            checks.evaluate("checks => checks.mark()")
            listed[index].click(timeout=2000)
            page.wait_for_timeout(150)
            if not checks.evaluate("checks => checks.popups()"):
                continue
            page.keyboard.press("Escape")
            page.wait_for_timeout(100)
            if not checks.evaluate("checks => checks.popups()"):
                continue
            found += checks.evaluate("checks => checks.findings()")
        except PlaywrightError:
            pass
        if checks is not None:
            checks.dispose()
        checks = None
        page.reload(wait_until="load")
        page.add_style_tag(content=STILL)
    if checks is not None:
        found += checks.evaluate("checks => checks.findings()")
        checks.dispose()
    return found


def crop_box(boxes, page_width, page_height):
    x1 = min(b[0] for b in boxes) - 24
    y1 = min(b[1] for b in boxes) - 24
    x2 = max(b[0] + b[2] for b in boxes) + 24
    y2 = max(b[1] + b[3] for b in boxes) + 24
    x1, y1 = max(x1, 0), max(y1, 0)
    x2, y2 = min(x2, page_width), min(y2, page_height)
    if x2 - x1 < 4 or y2 - y1 < 4:
        return None
    return {"x": x1, "y": y1, "width": x2 - x1, "height": y2 - y1}


def save(page, report, out, name):
    for old in out.glob(f"{name}-*.png"):
        old.unlink()
    frame = out / f"{name}.png"
    page.screenshot(path=str(frame), full_page=True)
    crops = []
    marked = [f for f in report["findings"] if f["boxes"]][:CROP_LIMIT]
    for finding in marked:
        clip = crop_box(finding["boxes"], max(report["width"], page.evaluate("document.documentElement.scrollWidth")), report["height"])
        if clip:
            path = out / f"{name}-{finding['id']}.png"
            page.screenshot(path=str(path), clip=clip, full_page=True)
            crops.append(path.name)
    (out / f"{name}.json").write_text(json.dumps(report, indent=1))
    return frame, crops


def short(values, limit=6):
    return " ".join(f"{v}×{c}" for v, c in values[:limit]) + (" …" if len(values) > limit else "")


SEEN = {}


def sources(page, items):
    wanted = [item for item in items if item.get("ref") and item["kind"] in PROPERTIES]
    if not wanted:
        return
    client = page.context.new_cdp_session(page)
    sheets = {}
    client.on("CSS.styleSheetAdded", lambda event: sheets.__setitem__(event["header"]["styleSheetId"], event["header"]))
    try:
        client.send("DOM.enable")
        client.send("CSS.enable")
        root = client.send("DOM.getDocument", {"depth": 0})["root"]["nodeId"]
        for item in wanted:
            node = client.send("DOM.querySelector", {"nodeId": root, "selector": f'[data-uic="{item["ref"]}"]'})["nodeId"]
            if node:
                item["source"] = source_of(client.send("CSS.getMatchedStylesForNode", {"nodeId": node}), PROPERTIES[item["kind"]], sheets)
    except PlaywrightError:
        return
    finally:
        client.detach()


def source_of(matched, names, sheets):
    inline = matched.get("inlineStyle") or {}
    if any(prop["name"] in names and prop.get("text") for prop in inline.get("cssProperties", [])):
        return "inline style"
    for entry in reversed(matched.get("matchedCSSRules", [])):
        rule = entry["rule"]
        if rule.get("origin") != "regular":
            continue
        props = [prop for prop in rule["style"].get("cssProperties", []) if prop["name"] in names and prop.get("text")]
        if not props:
            continue
        header = sheets.get(rule.get("styleSheetId")) or {}
        url = header.get("sourceURL") or ""
        line = rule["style"].get("range", {}).get("startLine", 0) + 1
        name = urlparse(url).path.rsplit("/", 1)[-1] if url else "inline <style>"
        declared = "; ".join(f"{prop['name']}: {prop['value']}" for prop in props[:2])
        return f"{name}:{line} {rule['selectorList']['text']} {{ {declared} }}"
    return None


def print_report(report, frame, crops, out, verbose=False):
    fails = sum(1 for f in report["findings"] if f["severity"] == "fail")
    warns = len(report["findings"]) - fails
    print(f"\n== {page_label(report['url'])} @ {report['width']}px ({report['mode']}): {fails} fail, {warns} warn, {len(report['smells'])} smell")
    groups = {}
    for item in report["findings"] + report["smells"]:
        groups.setdefault(item["id"][0] + item["kind"], []).append(item)
    page = page_label(report["url"])
    repeated = []
    for key, items in groups.items():
        first = items[0]
        mark = (page, key, first["elements"][0] if first["elements"] else "")
        if mark in SEEN and SEEN[mark] != report["width"]:
            repeated.append(first["kind"] + (f" ×{len(items)}" if len(items) > 1 else ""))
            continue
        SEEN.setdefault(mark, report["width"])
        count = f" ×{len(items)}" if len(items) > 1 else ""
        element = f" | {first['elements'][0]}" if first["elements"] else ""
        where = f" @ {first['source']}" if first.get("source") else ""
        print(f"  {key[0]} {first['kind']}{count}: {first['message']}{element}"[:240] + where[:160])
    if repeated:
        print(f"  same as at {min(SEEN[m] for m in SEEN if m[0] == page)}px: {', '.join(repeated)}")
    if verbose:
        lay = {k: ("–" if v is None else v) for k, v in report["layout"].items()}
        print(f"  layout   content x={lay['contentLeft']}..{lay['contentRight']} · header {lay['headerHeight']} · sidebar {lay['sidebarWidth']} · body {lay['bodyFont']} · h1 {lay['h1']} · radius {lay['radius']} · control {lay['controlHeight']} · icon {lay['iconSize']}")
        c = report["census"]
        print(f"  type     size {short(c['fontSize'])} · weight {short(c['fontWeight'], 4)} · family {short(c['fontFamily'], 3)}" + (f" · transform {short(c['textTransform'], 3)}" if c["textTransform"] else ""))
        print(f"  shape    radius {short(c['radius'])} · shadows {len(c['shadow'])} · gaps {short(c['gap'])}")
        print(f"  colour   text {short(c['color'], 5)} · fill {short(c['background'], 5)} · border {short(c['border'], 4)}")
        print(f"  frame    {frame}" + (f" · crops for {' '.join(p.rsplit('-', 1)[1][:-4] for p in crops)}" if crops else ""))


def page_differences(reports):
    by_width = {}
    for r in reports:
        by_width.setdefault(r["width"], []).append(r)
    lines = []
    for width, group in by_width.items():
        if len(group) < 2:
            continue
        for field in LAYOUT_FIELDS:
            values = {page_label(r["url"]): r["layout"][field] for r in group if r["layout"][field] is not None}
            if len(set(map(str, values.values()))) > 1:
                lines.append(f"  {width}px {field:<14}" + " · ".join(f"{k} {v}" for k, v in values.items()))
    return lines


def boxes(report):
    return [n["b"] for n in report["snapshot"] if n["b"][2] * n["b"][3] >= 400]


def matched(a, b):
    return sum(1 for box in a if any(all(abs(box[k] - other[k]) <= 8 for k in range(4)) for other in b))


def shared_layouts(reports):
    lines = []
    for i, a in enumerate(reports):
        for b in reports[i + 1:]:
            if a["width"] != b["width"]:
                continue
            first, second = boxes(a), boxes(b)
            if not first or not second:
                continue
            share = min(matched(first, second) / len(first), matched(second, first) / len(second))
            if share >= 0.8:
                lines.append(f"  {a['width']}px {page_label(a['url'])} and {page_label(b['url'])}: {round(share * 100)}% of boxes in the same place")
    return lines


def stress_failures(report, stressed):
    seen = {(f["kind"], tuple(f["elements"])) for f in report["findings"] if f["severity"] == "fail"}
    return [f for f in stressed["findings"] if f["severity"] == "fail" and (f["kind"], tuple(f["elements"])) not in seen]


def baseline_changes(report, old):
    before = {n["key"]: n for n in old["snapshot"]}
    after = {n["key"]: n for n in report["snapshot"]}
    restyled, resized, moved, shifted = [], [], [], []
    for key, now in after.items():
        was = before.get(key)
        if not was:
            continue
        if was["style"] != now["style"]:
            a, b = was["style"].split("|"), now["style"].split("|")
            changes = [f"{STYLE_FIELDS[k]} {a[k]} → {b[k]}" for k in range(min(len(a), len(b), len(STYLE_FIELDS))) if a[k] != b[k]]
            restyled.append(f"{now['name']}: {'; '.join(changes)}")
        dx, dy = now["b"][0] - was["b"][0], now["b"][1] - was["b"][1]
        dw, dh = now["b"][2] - was["b"][2], now["b"][3] - was["b"][3]
        if abs(dw) >= 1 or abs(dh) >= 1:
            resized.append((key.count(">"), f"{now['name']}: {was['b'][2]}×{was['b'][3]} → {now['b'][2]}×{now['b'][3]}"))
        elif abs(dx) >= 1:
            moved.append(f"{now['name']}: x {was['b'][0]} → {now['b'][0]}")
        elif abs(dy) >= 1:
            shifted.append(round(dy))
    new_keys = set(after) - set(before)
    gone_keys = set(before) - set(after)
    added = [k for k in after if k in new_keys and k.rsplit(">", 1)[0] not in new_keys]
    removed = [k for k in before if k in gone_keys and k.rsplit(">", 1)[0] not in gone_keys]
    resized.sort(key=lambda item: -item[0])
    lines = [f"  {len(restyled)} restyled, {len(resized)} resized, {len(moved)} moved sideways, {len(shifted)} moved up or down, {len(added)} added, {len(removed)} removed"]
    lines += [f"  restyled  {line}" for line in restyled[:15]]
    lines += [f"  resized   {line}" for _, line in resized[:10]]
    lines += [f"  moved     {line}" for line in moved[:10]]
    if shifted:
        lines.append(f"  shifted   {len(shifted)} elements, most by {max(set(shifted), key=shifted.count)}px")
    lines += [f"  added     {after[key]['name']}" for key in added[:10]]
    lines += [f"  removed   {before[key]['name']}" for key in removed[:10]]
    return lines


def main():
    parser = argparse.ArgumentParser(description="Measure a rendered page: alignment, spacing, overflow, overlap, contrast, slop smells. Draws the frame over a screenshot.")
    parser.add_argument("pages", nargs="+", help="URLs or local HTML files")
    parser.add_argument("--width", type=int, action="append", help="viewport width; repeat for more (default: 390 and 1280)")
    parser.add_argument("--height", type=int, default=900, help="viewport height (default: 900)")
    parser.add_argument("--mode", choices=["app", "marketing", "docs"], help="page type for the text checks; default: the script guesses")
    parser.add_argument("--interact", action="store_true", help="check keyboard focus and hover")
    parser.add_argument("--frame", choices=["issues", "all"], default="issues", help="issues: outline what was measured and mark findings; all: outline every element box")
    parser.add_argument("--out", type=pathlib.Path, default=pathlib.Path(tempfile.gettempdir()) / "ui-antislop", help="folder for screenshots and JSON")
    parser.add_argument("--baseline", type=pathlib.Path, help="an earlier --out folder; lists what changed since then")
    parser.add_argument("--stress", action="store_true", help="measure again with longer text and wider text spacing; lists the new fails")
    parser.add_argument("--verbose", action="store_true", help="also print the layout values, the census and the image paths")
    parser.add_argument("--variants", action="store_true", help="the pages are design options; lists pairs that share one layout")
    args = parser.parse_args()
    widths = args.width or [390, 1280]
    args.out.mkdir(parents=True, exist_ok=True)
    reports = []
    failed = False
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(device_scale_factor=1, reduced_motion="reduce")
        page = context.new_page()
        for arg in args.pages:
            url = as_url(arg)
            for width in widths:
                load(page, url, width, args.height)
                report = page.evaluate(PROBE, {"frame": args.frame, "mode": args.mode})
                sources(page, report["findings"] + report["smells"])
                name = f"{slug(url)}-{width}"
                frame, crops = save(page, report, args.out, name)
                print_report(report, frame, crops, args.out, args.verbose)
                failed = failed or any(f["severity"] == "fail" for f in report["findings"])
                if args.baseline:
                    old = args.baseline / f"{name}.json"
                    if old.exists():
                        print(f"\n== changes since baseline: {page_label(url)} @ {width}px")
                        print("\n".join(baseline_changes(report, json.loads(old.read_text()))))
                    else:
                        print(f"\n== no baseline for {name} in {args.baseline}")
                reports.append(report)
                if args.interact:
                    findings = interact(page)
                    (args.out / f"{name}-interact.json").write_text(json.dumps(findings, indent=1))
                    fails = sum(f["severity"] == "fail" for f in findings)
                    failed = failed or bool(fails)
                    print(f"\n== interact: {page_label(url)} @ {width}px: {fails} fail(s), {len(findings) - fails} warn(s)")
                    for f in findings:
                        print(f"  {'F' if f['severity'] == 'fail' else 'W'} {f['kind']}: {f['message']}" + (f" | {f['elements'][0]}" if f["elements"] else ""))
                    load(page, url, width, args.height)
                if args.stress:
                    page.evaluate(STRESS)
                    stressed = page.evaluate(PROBE, {"frame": args.frame, "mode": args.mode})
                    stress_frame, _ = save(page, stressed, args.out, f"{name}-stress")
                    new = stress_failures(report, stressed)
                    failed = failed or bool(new)
                    print(f"\n== stress: {page_label(url)} @ {width}px: {len(new)} new fail(s) with longer text")
                    by_kind = {}
                    for f in new:
                        by_kind.setdefault(f["kind"], []).append(f)
                    for kind, group in by_kind.items():
                        print(f"  F {kind} ×{len(group)}: {group[0]['message']}" + (f" | {group[0]['elements'][0]}" if group[0]["elements"] else ""))
                    load(page, url, width, args.height)
        browser.close()
    differences = page_differences(reports)
    if differences:
        print("\n== pages differ")
        print("\n".join(differences))
    if args.variants:
        same = shared_layouts(reports)
        print("\n== variants that share one layout" if same else "\n== variants: each layout is different")
        if same:
            print("\n".join(same))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
