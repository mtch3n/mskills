import collections
import importlib.util
import json
import pathlib
import re
import subprocess
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
SCRIPTS = HERE.parents[2] / "skills" / "ui-check" / "scripts"
PAGES = ["team", "projects", "settings"]
WIDTHS = [390, 1280]
ALLOWED = re.compile(r"^(site/[\w-]+\.(css|html)|DESIGN\.md)$")
RAW = {"raw-colour", "palette-class"}
LINK = "https://ledgerly.app/join/7f3a9c2e-design-team"
CHIPS = {"team": ["Owner", "Admin", "Billing", "Viewer"], "projects": ["New", "Active", "Closed"]}
BROKEN = {"control-cut", "clipped", "overflow-x"}

spec = importlib.util.spec_from_file_location("slop_lint", SCRIPTS / "slop-lint.py")
slop_lint = importlib.util.module_from_spec(spec)
spec.loader.exec_module(slop_lint)


def measure(site):
    out = pathlib.Path(tempfile.mkdtemp(prefix="ui-render-only-"))
    command = ["uv", "run", "--quiet", "--script", str(SCRIPTS / "ui-check.py"), *[str(site / f"{page}.html") for page in PAGES], "--stress", "--out", str(out)]
    for width in WIDTHS:
        command += ["--width", str(width)]
    subprocess.run(command, capture_output=True, text=True, timeout=900)
    reports = {}
    for page in PAGES:
        for width in WIDTHS:
            for suffix in ["", "-stress"]:
                path = out / f"{page}-{width}{suffix}.json"
                if path.exists():
                    reports[(page, width, suffix)] = json.loads(path.read_text())
    return reports


def kinds(report):
    return [f["kind"] for f in report["findings"]] + [s["kind"] for s in report["smells"]]


def chip_problems(report):
    return [f for f in report["findings"] if f["kind"] in {"inconsistent", "drift"} and any(".chip" in e or "span.chip" in e for e in f["elements"])]


def touches_copy(finding):
    return any('"Copy"' in e or "invite" in e or e.startswith("code") for e in finding["elements"])


def main_content(report):
    nodes = {n["key"]: n for n in report["snapshot"] if n["key"].startswith("main")}
    origin = nodes.get("main", {"b": [0, 0, 0, 0]})["b"]
    return {key: (round(n["b"][0] - origin[0]), round(n["b"][1] - origin[1]), round(n["b"][2]), round(n["b"][3]), n["style"]) for key, n in nodes.items()}


def added_lines(diff):
    lines = collections.defaultdict(list)
    current = None
    for line in diff.splitlines():
        if line.startswith("+++ "):
            current = line[6:] if line.startswith("+++ b/") else None
        elif current and line.startswith("+") and not line.startswith("+++"):
            lines[current].append(line[1:])
    return lines


def text_of(path):
    html = path.read_text(errors="replace") if path.exists() else ""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


def check(name, passed, weight, detail=""):
    return {"name": name, "passed": bool(passed), "weight": weight, "detail": detail}


def grade(run):
    workdir = pathlib.Path(run.workdir)
    before = measure(HERE / "fixture" / "site")
    after = measure(workdir / "site")
    expected = {(p, w, s) for p in PAGES for w in WIDTHS for s in ["", "-stress"]}
    measured = set(before) == set(after) == expected
    grades = [check("measured", measured, 0, f"{len(after)} of {len(expected)} reports")]
    if not measured:
        return grades

    left = [f"{f['kind']}@{w}" for w in WIDTHS for f in after[("team", w, "")]["findings"] if f["kind"] in BROKEN and touches_copy(f)]
    grades.append(check("fixed:copy-visible", not left, 2, ", ".join(left)))

    fragile = [f"{f['kind']}@{w}" for w in WIDTHS for f in after[("team", w, "-stress")]["findings"] if f["kind"] in BROKEN and touches_copy(f)]
    grades.append(check("robust:long-link", not fragile, 1, ", ".join(fragile)))

    for page, name, weight in [("team", "fixed:team-chips", 2), ("projects", "sweep:projects-chips", 2)]:
        uneven = [f"{w}px: {f['message'][:70]}" for w in WIDTHS for f in chip_problems(after[(page, w, "")])]
        grades.append(check(name, not uneven, weight, "; ".join(uneven)))

    team = text_of(workdir / "site" / "team.html")
    missing = [] if LINK in team else ["invite link"]
    for page, words in CHIPS.items():
        text = text_of(workdir / "site" / f"{page}.html")
        missing += [f"{page}:{w}" for w in words if w not in text]
    grades.append(check("scope:content-kept", not missing, 1, ", ".join(missing)))

    moved = [f"settings@{w}" for w in WIDTHS if main_content(after[("settings", w, "")]) != main_content(before[("settings", w, "")])]
    header = [f"{p}@{w}" for p in PAGES for w in WIDTHS if [n for n in after[(p, w, "")]["snapshot"] if n["key"].startswith("header")] != [n for n in before[(p, w, "")]["snapshot"] if n["key"].startswith("header")]]
    grades.append(check("scope:other-parts", not moved and not header, 1, ", ".join(moved + header)))

    lines = added_lines(run.diff)
    outside = sorted(path for path in lines if not ALLOWED.match(path))
    grades.append(check("scope:files", not outside, 1, ", ".join(outside)))

    raw = []
    for path, added in lines.items():
        if path.startswith("site/"):
            for text in added:
                raw += [f"{path}: {kind}: {text.strip()[:60]}" for kind, _ in slop_lint.check_line(pathlib.Path(path), text) if kind in RAW]
    grades.append(check("tokens:no-raw-values", not raw, 1, "; ".join(raw)[:300]))

    new = []
    for key in [(p, w, "") for p in PAGES for w in WIDTHS]:
        extra = collections.Counter(kinds(after[key])) - collections.Counter(kinds(before[key]))
        new += [f"{key[0]}@{key[1]}: {kind}" for kind in extra]
    grades.append(check("no-new-problems", not new, 1, "; ".join(new)))

    rules = lines.get("DESIGN.md", [])
    recorded = any(re.search(r"chip|copy|invite|em\b|rem\b|font size|font-size|min-width|phone|mobile|390", line, re.I) for line in rules)
    grades.append(check("rule:recorded", recorded, 1, " | ".join(rules)[:300]))

    grades.append({"name": "metrics", "passed": True, "weight": 0, "metrics": {
        "fails_before": sum(f["severity"] == "fail" for k, r in before.items() if not k[2] for f in r["findings"]),
        "fails_after": sum(f["severity"] == "fail" for k, r in after.items() if not k[2] for f in r["findings"]),
        "stress_fails_after": sum(f["severity"] == "fail" for k, r in after.items() if k[2] for f in r["findings"]),
    }})
    return grades
