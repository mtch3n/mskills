import collections
import importlib.util
import json
import pathlib
import re
import subprocess
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
SCRIPTS = HERE.parents[2] / "skills" / "ui-antislop" / "scripts"
PAGES = ["team", "settings"]
WIDTHS = [390, 1280]
ALLOWED = re.compile(r"^(site/[\w-]+\.css|site/team\.html|DESIGN\.md)$")
RAW = {"raw-colour", "palette-class"}
KEEP = ["https://ledgerly.app/join/7f3a9c2e-design-team", "Ana Silva", "Ben Okafor", "Chen Wei", "Owner", "Admin", "Billing", "Viewer", "Add member", "Copy", "Seats used", "12", "108"]
DEFECTS = [
    ("fixed:copy-visible", lambda r, i: [f for f in r["findings"] if f["kind"] in {"control-cut", "clipped", "overflow-x"}]),
    ("fixed:chips", lambda r, i: [f for f in r["findings"] if f["kind"] == "inconsistent" and any("chip" in e for e in f["elements"])]),
    ("fixed:icon", lambda r, i: [f for f in r["findings"] if f["kind"] == "icon-centre"]),
    ("fixed:table-header", lambda r, i: [f for f in r["findings"] if f["kind"] == "table-column"]),
    ("fixed:numbers", lambda r, i: [f for f in r["findings"] if f["kind"] == "numeric-align"]),
    ("fixed:focus", lambda r, i: [f for f in i if f["kind"] == "focus-invisible"]),
    ("fixed:helper-text", lambda r, i: [f for f in r["findings"] if f["kind"] in {"helper-text", "restates"}] + [s for s in r["smells"] if s["kind"] == "filler"]),
]

spec = importlib.util.spec_from_file_location("slop_lint", SCRIPTS / "slop-lint.py")
slop_lint = importlib.util.module_from_spec(spec)
spec.loader.exec_module(slop_lint)


def measure(site):
    out = pathlib.Path(tempfile.mkdtemp(prefix="ui-polish-"))
    command = ["uv", "run", "--quiet", "--script", str(SCRIPTS / "ui-antislop.py"), *[str(site / f"{page}.html") for page in PAGES], "--interact", "--out", str(out)]
    for width in WIDTHS:
        command += ["--width", str(width)]
    subprocess.run(command, capture_output=True, text=True, timeout=900)
    reports = {}
    for page in PAGES:
        for width in WIDTHS:
            base, extra = out / f"{page}-{width}.json", out / f"{page}-{width}-interact.json"
            if base.exists() and extra.exists():
                reports[(page, width)] = (json.loads(base.read_text()), json.loads(extra.read_text()))
    return reports


def kinds(pair):
    report, interact = pair
    return [f["kind"] for f in report["findings"]] + [s["kind"] for s in report["smells"]] + [f["kind"] for f in interact]


def visible(style):
    fields = style.split("|")
    return "|".join(value for k, value in enumerate(fields) if k != 6)


def main_content(report):
    nodes = {n["key"]: n for n in report["snapshot"] if n["key"].startswith("main")}
    origin = nodes.get("main", {"b": [0, 0, 0, 0]})["b"]
    return {key: (round(n["b"][0] - origin[0]), round(n["b"][1] - origin[1]), round(n["b"][2]), round(n["b"][3]), visible(n["style"])) for key, n in nodes.items()}


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
    expected = {(p, w) for p in PAGES for w in WIDTHS}
    measured = set(before) == set(after) == expected
    grades = [check("measured", measured, 0, f"{len(after)} of {len(expected)} reports")]
    if not measured:
        return grades

    for name, found in DEFECTS:
        left = [f"{w}px: {f['kind']}" for w in WIDTHS for f in found(*after[("team", w)])]
        grades.append(check(name, not left, 1, "; ".join(left)[:200]))

    team = text_of(workdir / "site" / "team.html")
    missing = [word for word in KEEP if word not in team]
    grades.append(check("scope:content-kept", not missing, 2, ", ".join(missing)))

    def head(report):
        return [(n["key"], [round(v) for v in n["b"]], visible(n["style"])) for n in report["snapshot"] if n["key"].startswith("header")]

    header = [f"{p}@{w}" for p in PAGES for w in WIDTHS if head(after[(p, w)][0]) != head(before[(p, w)][0])]
    settings = [f"settings@{w}" for w in WIDTHS if main_content(after[("settings", w)][0]) != main_content(before[("settings", w)][0])]
    grades.append(check("scope:other-parts", not header and not settings, 1, ", ".join(header + settings)))

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
    for key in expected:
        extra = collections.Counter(kinds(after[key])) - collections.Counter(kinds(before[key]))
        new += [f"{key[0]}@{key[1]}: {kind}" for kind in extra]
    grades.append(check("no-new-problems", not new, 1, "; ".join(new)))

    grades.append({"name": "metrics", "passed": True, "weight": 0, "metrics": {
        "defects_fixed": sum(1 for g in grades if g["name"].startswith("fixed:") and g["passed"]),
        "findings_before": sum(len(kinds(v)) for v in before.values()),
        "findings_after": sum(len(kinds(v)) for v in after.values()),
    }})
    return grades
