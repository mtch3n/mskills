import pathlib
import re
import subprocess

HERE = pathlib.Path(__file__).resolve().parent
UI_FILES = sorted(p.name for p in (HERE / "fixture" / "components" / "ui").iterdir())
ALLOWED = re.compile(r"^(app/.+\.tsx?|components/(?!ui/).+\.tsx?|components/ui/(?!(" + "|".join(re.escape(n) for n in UI_FILES) + r")$)[\w-]+\.tsx|DESIGN\.md|package\.json|pnpm-lock\.yaml)$")
NATIVE = re.compile(r"<(input|select|textarea|button|label)\b|type=[\"'{ ]*[\"']?(date|datetime-local)\b")
OTHER_DATE = re.compile(r"""from\s+["'](react-datepicker|react-date-picker|react-datetime[\w-]*|react-calendar|flatpickr|react-flatpickr|@mui/[\w/-]+|antd|@mantine/[\w-]+)["']""")


def changed_files(diff):
    return sorted({line[6:] for line in diff.splitlines() if line.startswith("+++ b/")})


def check(name, passed, weight, detail=""):
    return {"name": name, "passed": bool(passed), "weight": weight, "detail": detail}


def imports(source, name):
    return re.search(r"import\s*\{[^}]*\b" + name + r"\b[^}]*\}\s*from\s*[\"']@/components/ui/[\w-]+[\"']", source) is not None


def grade(run):
    workdir = pathlib.Path(run.workdir)
    files = changed_files(run.diff)
    code = [f for f in files if f.endswith((".tsx", ".ts")) and not f.startswith("components/ui/")]
    source = "\n".join((workdir / f).read_text(errors="replace") for f in code if (workdir / f).is_file())
    page = (workdir / "app/invoices/new/page.tsx").read_text(errors="replace") if (workdir / "app/invoices/new/page.tsx").is_file() else ""
    words = [w for w in ("Due date", "Status", "Draft", "Sent", "Paid") if w.lower() not in source.lower()]
    grades = [check("task:fields-added", not words, 2, ", ".join(words))]
    grades.append(check("task:form-kept", all(w in page for w in ("Customer", "Amount", "Create invoice")), 1))
    grades.append(check("shadcn:date-picker", imports(source, "Calendar") and imports(source, "Popover"), 1))
    grades.append(check("shadcn:status-control", imports(source, "Select") or imports(source, "RadioGroup") or imports(source, "ToggleGroup"), 1))
    native = sorted({m.group(0) for m in NATIVE.finditer(source)})
    grades.append(check("shadcn:no-native-elements", not native, 1, ", ".join(native)))
    other = OTHER_DATE.findall(source) + [w for w in ("react-datepicker", "flatpickr", "@mui", "antd") if w in (workdir / "package.json").read_text(errors="replace")]
    grades.append(check("shadcn:no-other-library", not other, 1, ", ".join(other)))
    ui_changed = [f for f in files if f.startswith("components/ui/") and pathlib.Path(f).name in UI_FILES]
    grades.append(check("scope:ui-files-unchanged", not ui_changed, 1, ", ".join(ui_changed)))
    outside = [f for f in files if not ALLOWED.match(f)]
    grades.append(check("scope:files", not outside, 1, ", ".join(outside)))
    grades.append({"name": "metrics", "passed": True, "weight": 0, "metrics": {"shadcn_ok": sum(1 for g in grades if g["name"].startswith("shadcn:") and g["passed"])}})
    return grades
