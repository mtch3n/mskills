import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
UI_FILES = sorted(p.name for p in (HERE / "fixture" / "components" / "ui").iterdir())
ALLOWED = re.compile(r"^(app/.+\.(tsx?|css)|components/(?!ui/).+\.tsx?|components/ui/(?!(" + "|".join(re.escape(n) for n in UI_FILES) + r")$)[\w-]+\.tsx|DESIGN\.md|package\.json|pnpm-lock\.yaml)$")
OFF_PALETTE = re.compile(r"\b(?:bg|text|border|ring|fill|stroke)-(?:teal|emerald|green|cyan|sky|blue|indigo|violet|purple)-\d+|#[0-9a-fA-F]{3,8}\b")
KEEP = ["Quarterly revenue", "Refunds by region", "Churn by plan", "Annual tax summary", "Reports", "Export", "Last 7 days", "Last 30 days", "Last 90 days", "No reports in this range", "report.owner", "report.status", "rows.length"]


def changed_files(diff):
    return sorted({line[6:] for line in diff.splitlines() if line.startswith("+++ b/")})


def check(name, passed, weight, detail=""):
    return {"name": name, "passed": bool(passed), "weight": weight, "detail": detail}


def imports(source, name):
    return re.search(r"import\s*\{[^}]*\b" + name + r"\b[^}]*\}\s*from\s*[\"']@/components/ui/[\w-]+[\"']", source) is not None


def read(workdir, name):
    path = workdir / name
    return path.read_text(errors="replace") if path.is_file() else ""


def grade(run):
    workdir = pathlib.Path(run.workdir)
    files = changed_files(run.diff)
    page = read(workdir, "app/reports/page.tsx")
    css = read(workdir, "app/globals.css")
    code = {p: p.read_text(errors="replace") for folder in ("app", "components") for p in (workdir / folder).rglob("*.tsx") if "components/ui/" not in p.as_posix()}

    off = sorted({m.group(0) for m in OFF_PALETTE.finditer(page + css)})
    grades = [check("fixed:no-off-palette-colour", not off, 1, ", ".join(off))]
    lucide = [p.name for p, text in code.items() if "lucide-react" in text]
    grades.append(check("fixed:no-lucide", not lucide, 1, ", ".join(lucide)))
    grades.append(check("fixed:phosphor-icons", "@phosphor-icons/react" in page, 1))
    grades.append(check("fixed:shadcn-select", imports(page, "Select") and "<select" not in page, 1))
    grades.append(check("fixed:shadcn-scroll-area", imports(page, "ScrollArea") and "webkit-scrollbar" not in css + page, 1))
    grades.append(check("fixed:shadcn-tooltip", imports(page, "Tooltip") and not re.search(r"\btitle=", page), 1))
    grades.append(check("fixed:shadcn-empty", imports(page, "Empty"), 1))

    missing = [w for w in KEEP if w not in page]
    grades.append(check("scope:content-kept", not missing, 2, ", ".join(missing)))
    ui_changed = [f for f in files if f.startswith("components/ui/") and pathlib.Path(f).name in UI_FILES]
    grades.append(check("scope:ui-files-unchanged", not ui_changed, 1, ", ".join(ui_changed)))
    outside = [f for f in files if not ALLOWED.match(f)]
    grades.append(check("scope:files", not outside, 1, ", ".join(outside)))
    grades.append({"name": "metrics", "passed": True, "weight": 0, "metrics": {"defects_fixed": sum(1 for g in grades if g["name"].startswith("fixed:") and g["passed"])}})
    return grades
