import json
import pathlib
import re
import subprocess
import sys
import tempfile
import urllib.parse

SCRIPTS = pathlib.Path(__file__).resolve().parent.parent / "skills" / "ui-antislop" / "scripts"
LINT = SCRIPTS / "slop-lint.py"
CHECK = SCRIPTS / "ui-antislop.py"
PAGES = re.compile(r"^\s*[-*]?\s*ui-antislop:\s*(\S.*)$")
DEV_PORTS = [3000, 3001, 5173, 5174, 4321, 4173, 8080, 8000, 5000]
STYLESHEET = re.compile(r"""<link\b[^>]*href=["']([^"':]+\.css)["']""")
REFERENCE = re.compile(r"""<(?:link|script|img)\b[^>]*(?:href|src)=["']([^"':#?]+)["']""")


def root_of(cwd):
    out = subprocess.run(["git", "-C", str(cwd), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    return pathlib.Path(out.stdout.strip()) if out.returncode == 0 else pathlib.Path(cwd)


def listed_pages(root):
    listed, base = [], None
    rules = root / "DESIGN.md"
    if rules.is_file():
        for line in rules.read_text(errors="replace").splitlines():
            match = PAGES.match(line)
            if match:
                for item in match.group(1).split():
                    if "://" in item and urllib.parse.urlparse(item).path in {"", "/"}:
                        base = item.rstrip("/")
                    listed.append(item if "://" in item else str(root / item))
    return listed, base


def html_files(root):
    tracked = subprocess.run(["git", "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard", "*.html", "*.htm"], capture_output=True, text=True)
    names = tracked.stdout.split() if tracked.returncode == 0 else [str(f.relative_to(root)) for f in root.rglob("*.htm*") if "node_modules" not in f.parts]
    return [root / name for name in names[:300]]


def label(page):
    return pathlib.Path(urllib.parse.urlparse(page).path).name or page


def stylesheets(pages):
    found = []
    for page in pages:
        path = pathlib.Path(page)
        if path.is_file():
            found += [str(path.parent / href) for href in STYLESHEET.findall(path.read_text(errors="replace")) if (path.parent / href).is_file()]
    return list(dict.fromkeys(found))


def lint(files, cwd):
    if not files:
        return ""
    result = subprocess.run([sys.executable, "-I", str(LINT), *files], capture_output=True, text=True, cwd=cwd, timeout=30)
    lines = result.stdout.strip().splitlines()
    if len(lines) <= 1:
        return ""
    return "\n".join(lines if len(lines) <= 21 else lines[:20] + [f"... {len(lines) - 21} more", lines[-1]])


def short(finding):
    element = f" | {finding['elements'][0]}" if finding.get("elements") else ""
    where = f" @ {finding['source']}" if finding.get("source") else ""
    return f"{finding['kind']}: {finding['message']}{element}"[:200] + where[:140]


def measure(pages, cwd, options, timeout):
    out = pathlib.Path(tempfile.mkdtemp(prefix="ui-hook-"))
    try:
        run = subprocess.run(["uv", "run", "--quiet", "--script", str(CHECK), *pages, *options, "--out", str(out)], capture_output=True, text=True, cwd=cwd, timeout=timeout)
        error = run.stderr.strip().splitlines()[-1:] if run.returncode not in (0, 1) else []
    except subprocess.TimeoutExpired:
        error = [f"timed out after {timeout} s"]
    found = {}

    def note(page, width, severity, item, extra=""):
        element = item["elements"][0] if item.get("elements") else ""
        key = (page, severity, item["kind"], item.get("source") or element)
        if key not in found:
            found[key] = {"widths": [], "line": f"{extra}{short(item)}", "elements": set()}
        found[key]["elements"].add(element)
        if width not in found[key]["widths"]:
            found[key]["widths"].append(width)

    measured = set()
    for base in sorted(out.glob("*.json")):
        if base.stem.endswith(("-stress", "-interact")):
            continue
        report = json.loads(base.read_text())
        page, width = label(report["url"]), report["width"]
        measured.add(page)
        for f in report["findings"]:
            note(page, width, "F" if f["severity"] == "fail" else "W", f)
        for item in report["smells"]:
            note(page, width, "S", item)
        stressed = base.with_name(base.stem + "-stress.json")
        if stressed.exists():
            seen = {(f["kind"], tuple(f["elements"])) for f in report["findings"] if f["severity"] == "fail"}
            for f in json.loads(stressed.read_text())["findings"]:
                if f["severity"] == "fail" and (f["kind"], tuple(f["elements"])) not in seen:
                    note(page, width, "F", f, "with longer text: ")
        interact = base.with_name(base.stem + "-interact.json")
        if interact.exists():
            for f in json.loads(interact.read_text()):
                note(page, width, "F" if f["severity"] == "fail" else "W", f)
    lines = []
    for (page, severity, _, _), value in found.items():
        widths = "/".join(f"{w}px" for w in sorted(value["widths"]))
        count = f" (×{len(value['elements'])})" if len(value["elements"]) > 1 else ""
        lines.append((page, severity, f"{severity} {page} @ {widths}{count} {value['line']}"))
    missing = [label(p) for p in pages if label(p) not in measured]
    if missing:
        reason = error[0] if error else "no report"
        lines += [(page, "F", f"F {page} not measured: {reason}") for page in missing]
    order = {"F": 0, "W": 1, "S": 2}
    return sorted(lines, key=lambda item: order[item[1]])
