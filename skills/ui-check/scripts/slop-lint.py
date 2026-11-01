#!/usr/bin/env python3
import functools
import pathlib
import re
import subprocess
import sys

STYLE = {".css", ".scss", ".sass", ".less"}
MARKUP = {".html", ".htm", ".jsx", ".tsx", ".vue", ".svelte", ".astro", ".mdx"}
UI = STYLE | MARKUP
TOKEN_FILE = re.compile(r"(token|theme|tailwind\.config|variables)", re.I)
CUSTOM_PROPERTY = re.compile(r"--[\w-]+\s*:[^;]*;?")
HUES = "red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose|slate|gray|grey|zinc|neutral|stone"
COMMENT = re.compile(r"^\s*(?://|/\*|\*|\{/\*|<!--)")
VENDOR = re.compile(r"(?:^|/)(?:node_modules|dist|build|\.next|components/ui)/")
ALLOW = re.compile(r"slop-lint allow ([\w-]+):[ \t]*(\S[^\n]*)")
CLASS_ATTR = re.compile(r"""class(?:Name)?\s*=\s*(?:\{\s*)?["'`]([^"'`]*)["'`]""")

RULES = [
    ("raw-colour", UI, re.compile(r"(?<![\w&/])#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})\b(?![\w-])|\b(?:rgba?|hsla?|oklch|oklab|lab|lch)\((?![^)]*var\()"), "raw colour value; use a colour token"),
    ("palette-class", MARKUP, re.compile(rf"\b(?:bg|text|border|ring|fill|stroke|from|via|to|outline|divide|decoration|accent|caret|placeholder)-(?:{HUES})-\d{{2,3}}\b"), "palette colour class; use a token class"),
    ("arbitrary-size", MARKUP, re.compile(r"(?<![\w-])-?(?:[pm][xytrblse]?|gap(?:-[xy])?|space-[xy]|text|leading|tracking|rounded(?:-[a-z]{1,2})?)-\[-?\d*\.?\d+(?:px|rem|em)\]"), "arbitrary size; use the spacing or type scale"),
    ("inline-style", MARKUP, re.compile(r"""style\s*=\s*(?:\{\{[^}]*|"[^"]*)\b\d+(?:px|rem)"""), "inline size; use a class or token"),
    ("gradient", UI, re.compile(r"\b(?:linear|radial|conic)-gradient\(|\bbg-gradient-to-|\bbg-(?:linear|radial|conic)-"), "gradient"),
    ("gradient-text", UI, re.compile(r"background-clip\s*:\s*text|\bbg-clip-text\b"), "gradient text"),
    ("glass", UI, re.compile(r"backdrop-filter\s*:\s*blur|\bbackdrop-blur"), "blurred see-through surface"),
    ("glow", UI, re.compile(rf"box-shadow\s*:\s*0(?:px)?\s+0(?:px)?\s+(?:[1-9]\d+)px|\bshadow-(?:{HUES})-\d|\bshadow-\[0_0_\d"), "glow shadow"),
    ("accent-stripe", UI, re.compile(r"\bborder-[lrse]-(?:2|4|8|\[\d+px\])\b|border-(?:left|right|inline-start|inline-end)(?:-width)?\s*:\s*[2-9]px"), "coloured stripe on one side"),
    ("purple", UI, re.compile(r"\b[a-z]+-(?:indigo|violet|purple)-\d{2,3}\b|#(?:6366f1|4f46e5|8b5cf6|7c3aed|a855f7|9333ea|6d28d9)\b", re.I), "stock violet or indigo accent"),
    ("emoji", MARKUP, re.compile("[\U0001F300-\U0001FAFF☀-⛿✀-➿]"), "emoji in UI text"),
    ("native-tooltip", MARKUP, re.compile(r"<[a-z][\w-]*\b[^<>]*\stitle\s*="), "browser title tooltip; use the library tooltip"),
    ("stock-copy", MARKUP, re.compile(r"\b(?:seamless(?:ly)?|supercharge|effortless(?:ly)?|empower|game-?chang\w*|cutting-edge|next-level|revolutioni[sz]e|world-class|unleash|skyrocket|best-in-class|all-in-one|blazing(?:ly)? fast|level up)\b", re.I), "marketing word"),
]


COMPONENT_MARKUP = {".jsx", ".tsx", ".vue", ".svelte", ".astro", ".mdx"}
NATIVE = re.compile(r"(?<!render=\{)<(select|button|textarea|input|dialog|details|progress|label|hr|table)\b([^<>]*)")
INPUT_TYPE = re.compile(r"""\stype\s*=\s*\{?\s*["']([\w-]+)["']""")
SHADCN = {
    "select": "select", "button": "button", "textarea": "textarea", "dialog": "dialog", "details": "collapsible",
    "progress": "progress", "label": "label", "hr": "separator", "table": "table",
    "checkbox": "checkbox", "radio": "radio-group", "range": "slider", "input": "input",
}
DATE_TYPES = {"date", "datetime-local", "month", "week"}
DATE_PICKER = "use the shadcn date picker: a Popover with a Calendar, and an Input type=time for the time"
BROWSER_DIALOG = re.compile(r"""\bwindow\.(?:alert|confirm|prompt)\(|(?<![\w.])(?:alert|confirm|prompt)\(\s*["'`]""")
ALIAS_UI = re.compile(r'"ui"\s*:\s*"([^"]+)"')
TS_PATHS = re.compile(r'"([^"]+)/\*"\s*:\s*\[\s*"([^"*]*)\*"')
TEST_FILE = re.compile(r"(?:\.(?:test|spec|stories)\.\w+$|(?:^|/)(?:__tests__|tests?|e2e)/)")
IMPORT = re.compile(r"""^(?!\s*import\s+type\b).*?(?:\bfrom\s+|\bimport\s+|\brequire\(\s*)["']([^"']+)["']""")
DATE_LIBRARIES = re.compile(r"^(?:react-datepicker|react-date-picker|react-datetime-picker|react-datetime|react-calendar|react-flatpickr|flatpickr|pikaday|vanilla-calendar[\w-]*|@mui/x-date-pickers[\w/-]*|@mantine/dates|react-day-picker)(?:/|$)")
FOREIGN_LIBRARIES = re.compile(r"^(?:@mui/material|@mui/joy|antd|@chakra-ui/[\w-]+|@mantine/core|react-bootstrap|primereact|@headlessui/react|react-select|react-tooltip|react-modal|react-toastify|react-hot-toast|@radix-ui/[\w-]+|@base-ui-components/react|@base-ui/react)(?:/|$)")


@functools.cache
def shadcn_ui(folder):
    for project in (folder, *folder.parents):
        config = project / "components.json"
        if config.is_file():
            break
        if (project / ".git").exists():
            return None
    else:
        return None
    alias = (ALIAS_UI.search(config.read_text(errors="replace")) or [None, "@/components/ui"])[1]
    candidates = []
    for tsconfig in sorted(project.glob("tsconfig*.json")):
        for prefix, target in TS_PATHS.findall(tsconfig.read_text(errors="replace")):
            if alias.startswith(prefix + "/"):
                candidates.append(project / target / alias[len(prefix) + 1:])
    tail = alias.split("/", 1)[1] if alias.startswith(("@/", "~/")) else alias
    candidates += [project / "src" / tail, project / tail]
    return next((c for c in candidates if c.is_dir()), candidates[-1])


def native_elements(text, ui):
    found = []
    for tag, attrs in NATIVE.findall(text):
        name = tag
        if tag == "input":
            kind = (INPUT_TYPE.search(attrs) or [None, "text"])[1].lower()
            if kind in {"hidden", "submit", "reset", "image"}:
                continue
            if kind in DATE_TYPES:
                found.append(("date-picker", f"native <input type={kind}> in a shadcn project; {DATE_PICKER} (`pnpm dlx shadcn@latest add calendar popover`)"))
                continue
            name = kind if kind in SHADCN else "input"
        component = SHADCN[name]
        have = any((ui / f"{component}{ext}").is_file() for ext in (".tsx", ".jsx", ".vue", ".svelte"))
        hint = f"use the shadcn component in {ui.name}/{component}" if have else f"add it with `pnpm dlx shadcn@latest add {component}` and use it"
        if tag == "table":
            hint += ", or the Data Table (Table with @tanstack/react-table) for sorting, filters or pages"
        found.append(("native-element", f"native <{tag}{' type=' + name if tag == 'input' and name != 'input' else ''}> in a shadcn project; {hint}"))
    if BROWSER_DIALOG.search(text):
        have = (ui / "alert-dialog.tsx").is_file()
        found.append(("native-element", "browser alert or confirm in a shadcn project; " + ("use the shadcn alert-dialog" if have else "add it with `pnpm dlx shadcn@latest add alert-dialog` and use it")))
    for module in IMPORT.findall(text):
        if DATE_LIBRARIES.match(module):
            found.append(("date-picker", f"{module} in a shadcn project; {DATE_PICKER}"))
        elif FOREIGN_LIBRARIES.match(module):
            found.append(("foreign-component", f"{module} in a shadcn project; use the shadcn component in {ui.name}/ for this part"))
    return found


def eyebrow(line):
    for classes in CLASS_ATTR.findall(line):
        words = set(classes.split())
        if "uppercase" in words and any(w.startswith("tracking-") for w in words) and words & {"text-xs", "text-[10px]", "text-[11px]", "text-[12px]", "text-sm"}:
            return True
    return False


def check_line(path, text, ui=None):
    suffix = path.suffix.lower()
    found = []
    if COMMENT.match(text):
        return []
    if ui and suffix in COMPONENT_MARKUP:
        found += native_elements(text, ui)
    for kind, exts, pattern, message in RULES:
        if suffix not in exts or (kind == "glass" and "inset-0" in text) or (kind == "accent-stripe" and "blockquote" in text):
            continue
        subject = text
        if kind == "raw-colour":
            if TOKEN_FILE.search(path.name):
                continue
            subject = CUSTOM_PROPERTY.sub("", text)
            subject = re.sub(r"rgba?\(\s*0[\s,]+0[\s,]+0\b[^)]*\)", "", subject)
            subject = re.sub(r"<meta\b[^>]*>", "", subject)
            subject = re.sub(r"href\s*=\s*[\"']#[^\"']*", "", subject)
            if suffix in STYLE and "{" in subject:
                subject = subject[subject.index("{"):]
        if pattern.search(subject):
            found.append((kind, message))
    if suffix in MARKUP and eyebrow(text):
        found.append(("eyebrow", "small upper-case label; check that it is not above a heading"))
    return found


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True).stdout


def changed_lines(root):
    lines = {}
    current = None
    number = 0
    for line in git(root, "diff", "HEAD", "-U0", "--no-color", "--no-ext-diff").splitlines():
        if line.startswith("+++ "):
            current = root / line[6:] if line.startswith("+++ b/") else None
        elif line.startswith("@@"):
            number = int(re.search(r"\+(\d+)", line).group(1))
        elif current and line.startswith("+"):
            lines.setdefault(current, []).append((number, line[1:]))
            number += 1
    for name in git(root, "ls-files", "--others", "--exclude-standard").splitlines():
        path = root / name
        if path.suffix.lower() in UI:
            lines[path] = list(enumerate(path.read_text(errors="replace").splitlines(), 1))
    return lines


def file_lines(paths):
    lines = {}
    for arg in paths:
        base = pathlib.Path(arg)
        files = [p for p in base.rglob("*") if p.is_file() and not VENDOR.search(p.as_posix())] if base.is_dir() else [base]
        for path in files:
            if path.suffix.lower() in UI:
                lines[path] = list(enumerate(path.read_text(errors="replace").splitlines(), 1))
    return lines


def lint(lines):
    results = []
    for path in sorted(lines):
        ui = None if TEST_FILE.search(path.as_posix()) else shadcn_ui(path.resolve().parent)
        if ui and "components/ui/" in path.as_posix() and lines[path]:
            number, text = lines[path][0]
            results.append((path, number, "shadcn-file", "you changed a generated shadcn component; keep the change only if the project rules allow it, else change the code that uses it", text.strip()))
        if path.suffix.lower() not in UI or VENDOR.search(path.as_posix()):
            continue
        for number, text in lines[path]:
            for kind, message in check_line(path, text, ui):
                results.append((path, number, kind, message, text.strip()))
        if ui and path.suffix.lower() in COMPONENT_MARKUP and path.is_file():
            results += data_table(path)
    return results


TABLE_TAG = re.compile(r"<(?:table|Table)\b")
HANDMADE_TABLE = re.compile(r"\b(?:set)?(?:sort(?:By|Key|Dir|Direction|Order|Column|Field)|pageIndex|pageSize|currentPage|rowsPerPage)\b", re.I)


def data_table(path):
    source = path.read_text(errors="replace")
    if "@tanstack/react-table" in source or not HANDMADE_TABLE.search(source):
        return []
    for number, text in enumerate(source.splitlines(), 1):
        if TABLE_TAG.search(text):
            return [(path, number, "data-table", "table with its own sorting or pages in a shadcn project; use the shadcn Data Table: the Table component with @tanstack/react-table", text.strip())]
    return []


def allowed(root):
    rules = root / "DESIGN.md"
    if not rules.is_file():
        return {}
    return dict(ALLOW.findall(rules.read_text(errors="replace")))


def main(argv):
    cwd = pathlib.Path.cwd()
    root = pathlib.Path(git(cwd, "rev-parse", "--show-toplevel").strip() or cwd)
    lines = file_lines(argv) if argv else changed_lines(root)
    allow = allowed(root)
    results = [r for r in lint(lines) if r[2] not in allow]
    for path, number, kind, message, text in results:
        shown = path.relative_to(cwd) if path.is_relative_to(cwd) else path
        print(f"{shown}:{number}: {kind}: {message} | {text[:120]}")
    for kind, reason in allow.items():
        print(f"allowed by DESIGN.md: {kind}: {reason.strip()}")
    print(f"{len(results)} finding(s) in {len(lines)} file(s)")
    return 1 if results else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
