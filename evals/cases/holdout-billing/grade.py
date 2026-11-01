import json
import pathlib
import re
import subprocess

HERE = pathlib.Path(__file__).resolve().parent
ALLOWED = re.compile(r"^(site/[\w-]+\.css|site/billing\.html|DESIGN\.md)$")
INVOICES = ["INV-2026-000184-NORTHWIND-EU", "INV-2026-000163-NORTHWIND-EU", "INV-2026-000141-NORTHWIND-EU"]
KEEP = ["Starter", "Team", "Business", "$0", "$79", "Download PDF", "Send again", "Void invoice", *INVOICES]


def measure(site):
    result = subprocess.run(["uv", "run", "--quiet", "--script", str(HERE / "check.py"), str(site)], capture_output=True, text=True, timeout=300)
    return json.loads(result.stdout) if result.returncode == 0 and result.stdout.strip() else None


def changed_files(diff):
    return sorted({line[6:] for line in diff.splitlines() if line.startswith("+++ b/")})


def check(name, passed, weight, detail=""):
    return {"name": name, "passed": bool(passed), "weight": weight, "detail": detail}


def grade(run):
    workdir = pathlib.Path(run.workdir)
    before = measure(HERE / "fixture" / "site")
    after = measure(workdir / "site")
    grades = [check("measured", before and after, 0)]
    if not (before and after):
        return grades
    phone, desk = after["390"], after["1280"]

    bottoms = {b["bottom"] for b in desk["planButtons"]}
    grades.append(check("fixed:plan-buttons-aligned", len(desk["planButtons"]) == 3 and max(bottoms) - min(bottoms) <= 1, 1, str(desk["planButtons"])[:200]))
    radii = {b["radius"] for b in desk["planButtons"]}
    grades.append(check("fixed:plan-buttons-one-radius", len(radii) == 1, 1, ", ".join(sorted(radii))))

    wide = [f"{w}px page scrolls sideways" for w in ("390", "1280") if after[w]["scrollWidth"] > int(w)]
    cut = [f"{w}px: {text}" for w in ("390", "1280") for text in after[w]["cells"]]
    found = {i["text"] for i in phone["invoices"]}
    grades.append(check("fixed:table-fits", not wide and not cut and found == set(INVOICES), 1, "; ".join(wide + cut)[:200] or str(sorted(found))))

    menu = [f"{w}: {m['text']}" for w in ("390", "1280") for m in after[w]["menu"] if not m["reachable"]]
    opened = all(len(after[w]["menu"]) >= 3 for w in ("390", "1280"))
    grades.append(check("fixed:row-menu-visible", opened and not menu, 1, "; ".join(menu) or ("menu did not open" if not opened else "")))

    low = [c for w in ("390", "1280") for c in after[w]["dueContrast"] if c < 4.5]
    grades.append(check("fixed:date-contrast", desk["dueContrast"] and not low, 1, str(low[:3])))

    text = desk["pageText"]
    slop = [w for w in ("🚀", "Supercharge", "seamless", "effortless") if w.lower() in text.lower()]
    grades.append(check("fixed:lead-copy", not slop, 1, ", ".join(slop)))

    source = (workdir / "site" / "billing.html").read_text(errors="replace") if (workdir / "site" / "billing.html").is_file() else ""
    menu_items = ["Download PDF", "Send again", "Void invoice"]
    missing = [w for w in KEEP if w not in (source if w in menu_items else text)] + ([] if desk["amounts"] >= 3 else ["$24.00 x3"])
    grades.append(check("scope:content-kept", not missing, 2, ", ".join(missing)))

    header = [w for w in ("390", "1280") if after[w]["header"] != before[w]["header"]]
    account = [w for w in ("390", "1280") if after[w]["account"] != before[w]["account"]]
    grades.append(check("scope:other-parts", not header and not account, 1, f"header {header} account {account}"))

    outside = [path for path in changed_files(run.diff) if not ALLOWED.match(path)]
    grades.append(check("scope:files", not outside, 1, ", ".join(outside)))

    grades.append({"name": "metrics", "passed": True, "weight": 0, "metrics": {
        "defects_fixed": sum(1 for g in grades if g["name"].startswith("fixed:") and g["passed"]),
    }})
    return grades
