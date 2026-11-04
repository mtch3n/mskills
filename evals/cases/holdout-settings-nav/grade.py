import json
import pathlib
import re
import subprocess

HERE = pathlib.Path(__file__).resolve().parent
ALLOWED = re.compile(r"^(site/[\w-]+\.css|site/settings\.html|DESIGN\.md)$")
LINKS = ["Profile", "Password", "Notifications", "Members", "Billing", "Domains", "API keys", "Webhooks"]


def measure(site):
    result = subprocess.run(["uv", "run", "--quiet", "--script", str(HERE / "check.py"), str(site)], capture_output=True, text=True, timeout=300)
    return json.loads(result.stdout) if result.returncode == 0 and result.stdout.strip() else None


def changed_files(diff):
    return sorted({line[6:] for line in diff.splitlines() if line.startswith("+++ b/")})


def check(name, passed, weight, detail=""):
    return {"name": name, "passed": bool(passed), "weight": weight, "detail": detail}


def group_gap(facts):
    links = facts["links"]
    steps = [b["top"] - a["bottom"] for a, b in zip(links, links[1:]) if not any(t and a["bottom"] <= t["top"] < b["top"] for t in facts["titles"])]
    above = [t["top"] - max((l["bottom"] for l in links if l["bottom"] <= t["top"]), default=t["top"]) for t in facts["titles"][1:] if t]
    return (max(steps) if steps else None), above


def grade(run):
    workdir = pathlib.Path(run.workdir)
    before = measure(HERE / "fixture" / "site")
    after = measure(workdir / "site")
    grades = [check("measured", before and after, 0)]
    if not (before and after):
        return grades
    desk, phone = after["1280"], after["390"]
    titles = [t for t in desk["titles"] if t]
    links = desk["links"]

    differ = bool(links) and len(titles) == 3 and all(any(t[k] != links[0][k] for k in ("weight", "color", "size", "transform")) for t in titles)
    grades.append(check("fixed:titles-look-different", differ, 1))
    step, above = group_gap(desk)
    spaced = step is not None and len(above) == 2 and all(a >= step + 6 for a in above)
    grades.append(check("fixed:groups-separated", spaced, 1, f"link gap {step}, above titles {above}"))
    idle = len(titles) == 3 and not any(t["clickable"] or t["cursor"] == "pointer" for t in titles)
    grades.append(check("fixed:titles-not-clickable", idle, 1, str([t["cursor"] for t in titles])))
    grades.append(check("fixed:titles-no-hover", len(desk["titleHover"]) == 3 and not any(desk["titleHover"]), 1, str(desk["titleHover"])))
    hints = desk["hints"]
    rights = {h["right"] for h in hints}
    offsets = [h["offset"] for h in hints if h["offset"] is not None]
    aligned = len(hints) == 6 and (max(rights) - min(rights) <= 1 or (len(offsets) == 6 and max(offsets) - min(offsets) <= 1))
    grades.append(check("fixed:hints-aligned", aligned, 1, str(sorted(rights))))

    names = [l["text"] for l in links]
    missing = [w for w in LINKS if w not in names] + [w for w in ("Account", "Workspace", "Developer") if w.lower() not in [t["text"].lower() for t in titles]]
    grades.append(check("scope:content-kept", not missing and len({l["href"] for l in links}) == 8, 2, ", ".join(missing)))
    grades.append(check("scope:main-unchanged", desk["mainLook"] == before["1280"]["mainLook"] and desk["mainText"] == before["1280"]["mainText"], 1))
    grades.append(check("scope:links-look-clickable", all(l["cursor"] == "pointer" for l in links), 1))
    wide = [w for w, facts in (("1280", desk), ("390", phone)) if facts["scrollWidth"] > int(w)]
    grades.append(check("scope:no-sideways-scroll", not wide, 1, ", ".join(wide)))
    outside = [path for path in changed_files(run.diff) if not ALLOWED.match(path)]
    grades.append(check("scope:files", not outside, 1, ", ".join(outside)))
    grades.append({"name": "metrics", "passed": True, "weight": 0, "metrics": {"defects_fixed": sum(1 for g in grades if g["name"].startswith("fixed:") and g["passed"])}})
    return grades
