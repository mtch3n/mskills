import json
import pathlib
import re
import subprocess

HERE = pathlib.Path(__file__).resolve().parent
ALLOWED = re.compile(r"^(site/[\w-]+\.css|site/leads\.html|DESIGN\.md)$")
LEADS = ["Ana Ferreira", "Tomas Lind", "Priya Nair", "Sam Okafor", "Jo Whitaker", "Mei Tanaka"]
KEEP = [*LEADS, "Harbor Foods", "Contract ends in March.", "Call", "Email", "Export", "New lead", "This week"]
STAGES = ["Pipeline", "Stages", "Contacted", "Proposal", "Won"]


def measure(site):
    result = subprocess.run(["uv", "run", "--quiet", "--script", str(HERE / "check.py"), str(site)], capture_output=True, text=True, timeout=300)
    return json.loads(result.stdout) if result.returncode == 0 and result.stdout.strip() else None


def changed_files(diff):
    return sorted({line[6:] for line in diff.splitlines() if line.startswith("+++ b/")})


def check(name, passed, weight, detail=""):
    return {"name": name, "passed": bool(passed), "weight": weight, "detail": detail}


def grade(run):
    workdir = pathlib.Path(run.workdir)
    after = measure(workdir / "site")
    grades = [check("measured", after, 0)]
    if not after:
        return grades
    desk, phone = after["1280"], after["390"]

    bar = desk["toolbar"]
    grades.append(check("fixed:toolbar-one-height", len(bar) == 3 and max(bar) - min(bar) <= 1 and max(bar) <= 40, 1, str(bar)))
    inset = desk["inset"]
    grades.append(check("fixed:container-padding", inset is not None and inset <= 50, 1, str(inset)))
    grades.append(check("fixed:no-container-shadow", desk["shadows"] == 0, 1, str(desk["shadows"])))
    grades.append(check("fixed:no-card-in-card", desk["nested"] == 0, 1, str(desk["nested"])))
    grades.append(check("fixed:footer-plain", desk["footers"] == 6 and desk["painted"] == 0, 1, f'{desk["painted"]} of {desk["footers"]}'))
    side = desk["sidebar"]
    grades.append(check("fixed:sidebar-narrower", side is not None and side <= 260, 1, str(side)))

    small = [h for w in (desk, phone) for h in w["buttonHeights"] if h < 28]
    grades.append(check("scope:not-too-compact", not small and min(desk["smallest"], phone["smallest"]) >= 12 and (inset or 0) >= 8, 1, f'{small[:3]} font {desk["smallest"]} inset {inset}'))
    missing = [w for w in KEEP if w not in desk["text"]] + [w for w in STAGES if w not in after["pipeline1280"]["text"]]
    grades.append(check("scope:content-kept", not missing, 2, ", ".join(missing)))
    wide = [f"{name} {w}" for name, w in (("leads", desk["scrollWidth"] - 1280), ("leads phone", phone["scrollWidth"] - 390), ("pipeline phone", after["pipeline390"]["scrollWidth"] - 390)) if w > 0]
    grades.append(check("scope:no-sideways-scroll", not wide, 1, ", ".join(wide)))
    outside = [path for path in changed_files(run.diff) if not ALLOWED.match(path)]
    grades.append(check("scope:files", not outside, 1, ", ".join(outside)))
    grades.append({"name": "metrics", "passed": True, "weight": 0, "metrics": {"defects_fixed": sum(1 for g in grades if g["name"].startswith("fixed:") and g["passed"])}})
    return grades
