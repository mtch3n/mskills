import collections
import json
import pathlib
import re
import subprocess
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
UI_CHECK = HERE.parents[2] / "skills" / "ui-check" / "scripts" / "ui-check.py"
PAGES = ["files", "shared", "settings"]
WIDTHS = [390, 1280]
ALLOWED = re.compile(r"^(site/[\w-]+\.(css|html)|DESIGN\.md)$")
CONTROL = re.compile(r"(^|>)(input|button)\d*$")


def measure(site):
    out = pathlib.Path(tempfile.mkdtemp(prefix="ui-complaint-"))
    command = ["uv", "run", "--quiet", "--script", str(UI_CHECK), *[str(site / f"{page}.html") for page in PAGES], "--out", str(out)]
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


def problems(report):
    return [f["kind"] for f in report["findings"]] + [s["kind"] for s in report["smells"]]


def part(report, test):
    return {n["key"]: (n["b"], n["style"]) for n in report["snapshot"] if test(n["key"])}


def added_lines(diff, path):
    lines = []
    inside = False
    for line in diff.splitlines():
        if line.startswith("+++ "):
            inside = line == f"+++ b/{path}"
        elif inside and line.startswith("+") and not line.startswith("+++"):
            lines.append(line[1:])
    return lines


def changed_files(diff):
    return {line[6:] for line in diff.splitlines() if line.startswith("+++ b/")}


def check(name, passed, weight, detail=""):
    return {"name": name, "passed": bool(passed), "weight": weight, "detail": detail}


def grade(run):
    before = measure(HERE / "fixture" / "site")
    after = measure(pathlib.Path(run.workdir) / "site")
    measured = set(before) == set(after) == {(p, w) for p in PAGES for w in WIDTHS}
    grades = [check("measured", measured, 0, f"{len(after)} of {len(PAGES) * len(WIDTHS)} reports")]
    if not measured:
        return grades

    def clear(page, kind):
        left = [f"{w}px" for w in WIDTHS if kind in problems(after[(page, w)])]
        return not left, ", ".join(left)

    for name, page, kind, weight in [
        ("fixed:files-table", "files", "table-column", 2),
        ("sweep:shared-table", "shared", "table-column", 2),
        ("fixed:settings-nesting", "settings", "card-in-card", 2),
    ]:
        passed, detail = clear(page, kind)
        grades.append(check(name, passed, weight, detail))

    new = []
    for key in after:
        extra = collections.Counter(problems(after[key])) - collections.Counter(problems(before[key]))
        new += [f"{key[0]}@{key[1]}: {kind}" for kind in extra]
    grades.append(check("no-new-problems", not new, 1, "; ".join(new)))

    header_moved = [f"{p}@{w}" for (p, w) in after if part(after[(p, w)], lambda k: k.startswith("header")) != part(before[(p, w)], lambda k: k.startswith("header"))]
    grades.append(check("scope:header-unchanged", not header_moved, 2, ", ".join(header_moved)))

    def sizes(report):
        return sorted((n["name"], n["b"][2], n["b"][3]) for n in report["snapshot"] if CONTROL.search(n["key"]))

    resized = [f"{p}@{w}" for (p, w) in after if sizes(after[(p, w)]) != sizes(before[(p, w)])]
    grades.append(check("scope:controls-unchanged", not resized, 1, ", ".join(resized)))

    outside = sorted(path for path in changed_files(run.diff) if not ALLOWED.match(path))
    grades.append(check("scope:files", not outside, 1, ", ".join(outside)))

    rules = added_lines(run.diff, "DESIGN.md")
    nesting = any(re.search(r"card|box|surface", line, re.I) and re.search(r"inside|within|nest|wrap|in a ", line, re.I) for line in rules)
    table = any(re.search(r"header|heading|column|\bth\b", line, re.I) and re.search(r"align|line up|lines up", line, re.I) for line in rules)
    grades.append(check("rule:nesting-recorded", nesting, 1, " | ".join(rules)[:300]))
    grades.append(check("rule:table-recorded", table, 1, " | ".join(rules)[:300]))

    warns_before = sum(len(r["findings"]) for r in before.values())
    warns_after = sum(len(r["findings"]) for r in after.values())
    smells_after = sum(len(r["smells"]) for r in after.values())
    grades.append({"name": "metrics", "passed": True, "weight": 0, "metrics": {"findings_before": warns_before, "findings_after": warns_after, "smells_after": smells_after}})
    return grades
