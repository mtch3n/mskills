import collections
import importlib.util
import json
import pathlib
import re
import subprocess
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
SCRIPTS = HERE.parents[2] / "skills" / "ui-antislop" / "scripts"
PAGES = ["dashboard", "invoices", "settings"]
WIDTHS = [390, 1280]
ALLOWED = re.compile(r"^(site/[\w-]+\.(css|html)|DESIGN\.md)$")
SLOP = {"gradient", "accent-stripe", "icon-tile", "eyebrow", "card-grid", "tinted-box"}
RAW = {"raw-colour", "palette-class", "arbitrary-size", "inline-style"}
NUMBERS = [r"Revenue this month\s*\$12,400|\$12,400\s*Revenue this month", r"Open invoices\s*38\b|\b38\s*Open invoices", r"Overdue\s*4\b|\b4\s*Overdue"]

spec = importlib.util.spec_from_file_location("slop_lint", SCRIPTS / "slop-lint.py")
slop_lint = importlib.util.module_from_spec(spec)
spec.loader.exec_module(slop_lint)


def measure(site):
    out = pathlib.Path(tempfile.mkdtemp(prefix="ui-slop-dashboard-"))
    command = ["uv", "run", "--quiet", "--script", str(SCRIPTS / "ui-antislop.py"), *[str(site / f"{page}.html") for page in PAGES], "--out", str(out)]
    for width in WIDTHS:
        command += ["--width", str(width)]
    subprocess.run(command, capture_output=True, text=True, timeout=600)
    reports = {}
    for page in PAGES:
        for width in WIDTHS:
            path = out / f"{page}-{width}.json"
            if path.exists():
                reports[(page, width)] = json.loads(path.read_text())
    return reports


def findings(report):
    return [f["kind"] for f in report["findings"]]


def smells(report):
    return [s["kind"] for s in report["smells"]]


def main_content(report):
    nodes = {n["key"]: n for n in report["snapshot"] if n["key"].startswith("div>main")}
    origin = nodes.get("div>main", {"b": [0, 0, 0, 0]})["b"]
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
    measured = set(before) == set(after) == {(p, w) for p in PAGES for w in WIDTHS}
    grades = [check("measured", measured, 0, f"{len(after)} of {len(PAGES) * len(WIDTHS)} reports")]
    if not measured:
        return grades

    left = [f"{p}@{w}" for (p, w), r in after.items() if {"icon-centre", "off-centre"} & set(findings(r))]
    grades.append(check("fixed:sidebar-icons", not left, 2, ", ".join(left)))

    remaining = sorted({kind for w in WIDTHS for kind in smells(after[("dashboard", w)]) if kind in SLOP})
    grades.append(check("fixed:dashboard-slop", not remaining, 2, ", ".join(remaining)))

    dashboard = text_of(workdir / "site" / "dashboard.html")
    grades.append(check("rule:helper-removed", "quick look at how your business" not in dashboard, 1))
    missing = [pattern.split("\\s")[0] for pattern in NUMBERS if not re.search(pattern, dashboard)]
    grades.append(check("scope:numbers-kept", not missing, 2, ", ".join(missing)))

    moved = [f"{p}@{w}" for p in ["invoices", "settings"] for w in WIDTHS if main_content(after[(p, w)]) != main_content(before[(p, w)])]
    grades.append(check("scope:other-pages", not moved, 1, ", ".join(moved)))

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
    for key in after:
        extra = collections.Counter(findings(after[key]) + smells(after[key])) - collections.Counter(findings(before[key]) + smells(before[key]))
        new += [f"{key[0]}@{key[1]}: {kind}" for kind in extra]
    grades.append(check("no-new-problems", not new, 1, "; ".join(new)))

    rules = lines.get("DESIGN.md", [])
    recorded = any(re.search(r"icon|gradient|stripe|tile|eyebrow|decorat|label above|ai[- ]generated|slop", line, re.I) for line in rules)
    grades.append(check("rule:recorded", recorded, 1, " | ".join(rules)[:300]))

    grades.append({"name": "metrics", "passed": True, "weight": 0, "metrics": {
        "findings_before": sum(len(r["findings"]) for r in before.values()),
        "findings_after": sum(len(r["findings"]) for r in after.values()),
        "smells_after": sum(len(r["smells"]) for r in after.values()),
    }})
    return grades
