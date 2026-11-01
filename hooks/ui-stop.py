#!/usr/bin/env python3
import datetime
import hashlib
import json
import os
import pathlib
import re
import subprocess
import socket
import sys
import tempfile
import urllib.parse

UI = (".css", ".scss", ".sass", ".less", ".html", ".htm", ".jsx", ".tsx", ".vue", ".svelte", ".astro", ".mdx")
UI_PATH = re.compile(r"[\w./~@+-]+(?:" + "|".join(re.escape(e) for e in UI) + r")\b")
WRITES = re.compile(r"\bsed\s+-i|\bperl\s+-p?i|>|\btee\b|\bpython3?\b|\bmv\b|\bcp\b|\bpatch\b|\bgit\s+apply\b")
MEASURE = re.compile(r"ui-check\.py|probe\.js")
EDIT_TOOLS = {"Edit", "Write", "MultiEdit"}
SCRIPTS = pathlib.Path(__file__).resolve().parent.parent / "skills" / "ui-check" / "scripts"
LINT = SCRIPTS / "slop-lint.py"
CHECK = SCRIPTS / "ui-check.py"
PAGES = re.compile(r"^\s*[-*]?\s*ui-check:\s*(\S.*)$")
ROUNDS = 3
FIXTURE = re.compile(r"/(tests?|__tests__|fixtures?|__fixtures__|evals)/")
DEV_PORTS = [3000, 3001, 5173, 5174, 4321, 4173, 8080, 8000, 5000]
ROUTES = [re.compile(p) for p in [r"^(?:src/)?app/(.*?)/?page\.(?:tsx|jsx|ts|js|mdx)$", r"^(?:src/)?pages/(.*?)\.(?:tsx|jsx|astro|vue|svelte|mdx)$", r"^src/routes/(.*?)/?\+page\.svelte$"]]


def events(transcript):
    with open(transcript, encoding="utf-8") as handle:
        for line in handle:
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def tool_uses(event):
    content = (event.get("message") or {}).get("content")
    if event.get("type") != "assistant" or not isinstance(content, list):
        return []
    return [item for item in content if isinstance(item, dict) and item.get("type") == "tool_use"]


def started(event):
    stamp = event.get("timestamp")
    if not stamp:
        return None
    return datetime.datetime.fromisoformat(stamp.replace("Z", "+00:00")).timestamp()


def resolve(cwd, name):
    return pathlib.Path(os.path.expanduser(name)) if name.startswith(("/", "~")) else pathlib.Path(cwd) / name


def touched(use, cwd):
    name = use.get("name")
    data = use.get("input") or {}
    if name in EDIT_TOOLS:
        path = data.get("file_path") or ""
        return [resolve(cwd, path)] if path.endswith(UI) else []
    if name == "Bash":
        command = data.get("command") or ""
        if MEASURE.search(command) or not WRITES.search(command):
            return []
        return [resolve(cwd, found) for found in UI_PATH.findall(command)]
    return []


def changed_files(transcript, cwd):
    start = None
    files = set()
    for event in events(transcript):
        start = start or started(event)
        for use in tool_uses(event):
            files.update(touched(use, cwd))
    if start is None:
        return []
    return sorted(str(p) for p in files if p.is_file() and p.stat().st_mtime >= start and not FIXTURE.search(p.as_posix()))


def measured_after_edit(transcript, cwd):
    last_edit = last_measure = -1
    for index, event in enumerate(events(transcript)):
        for use in tool_uses(event):
            if use.get("name") == "Bash" and MEASURE.search((use.get("input") or {}).get("command") or ""):
                last_measure = index
            if touched(use, cwd):
                last_edit = index
    return last_measure > last_edit


def lint(files, cwd):
    result = subprocess.run([sys.executable, "-I", str(LINT), *files], capture_output=True, text=True, cwd=cwd, timeout=30)
    lines = result.stdout.strip().splitlines()
    if len(lines) <= 1:
        return ""
    return "\n".join(lines if len(lines) <= 21 else lines[:20] + [f"... {len(lines) - 21} more", lines[-1]])


def root_of(cwd):
    out = subprocess.run(["git", "-C", str(cwd), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    return pathlib.Path(out.stdout.strip()) if out.returncode == 0 else pathlib.Path(cwd)


def route_of(path, root):
    rel = pathlib.Path(path).resolve().relative_to(root).as_posix() if pathlib.Path(path).resolve().is_relative_to(root) else ""
    for pattern in ROUTES:
        match = pattern.match(rel)
        if match:
            parts = [p for p in match.group(1).split("/") if p and not p.startswith("(") and p not in {"index"}]
            if any(p.startswith("[") or p.startswith("_") for p in parts):
                return None
            return "/" + "/".join(parts)
    return None


def dev_server():
    for port in DEV_PORTS:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2) as conn:
                conn.sendall(b"GET / HTTP/1.0\r\nHost: localhost\r\n\r\n")
                head = conn.recv(4096).lower()
                if b"<html" in head or b"text/html" in head:
                    return f"http://localhost:{port}"
        except OSError:
            continue
    return None


def pages_for(files, cwd):
    root = root_of(cwd)
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
    pages = [f for f in files if f.endswith((".html", ".htm"))]
    assets = {pathlib.Path(f).name for f in files if not f.endswith((".html", ".htm"))}
    if assets:
        tracked = subprocess.run(["git", "-C", str(root), "ls-files", "*.html", "*.htm"], capture_output=True, text=True)
        names = tracked.stdout.split() if tracked.returncode == 0 else [str(f.relative_to(root)) for f in root.rglob("*.htm*") if "node_modules" not in f.parts]
        for name in names[:300]:
            path = root / name
            if str(path) not in pages and path.is_file() and any(asset in path.read_text(errors="replace") for asset in assets):
                pages.append(str(path))
    routes = [r for r in (route_of(f, root) for f in files) if r is not None]
    server = base or ((routes or not pages) and dev_server())
    if server:
        pages += [server + r for r in dict.fromkeys(routes or ["/"])]
    pages += [item for item in listed if item not in pages and not (base and item.rstrip("/") == base)]
    return list(dict.fromkeys(pages))[:6]


def short(finding):
    element = f" | {finding['elements'][0]}" if finding.get("elements") else ""
    return f"{finding['kind']}: {finding['message']}{element}"[:200]


def measure(pages, cwd):
    out = pathlib.Path(tempfile.mkdtemp(prefix="ui-stop-"))
    subprocess.run(["uv", "run", "--quiet", "--script", str(CHECK), *pages, "--stress", "--interact", "--out", str(out)], capture_output=True, text=True, cwd=cwd, timeout=270)
    found = {}

    def note(page, width, severity, item, extra=""):
        key = (page, severity, item["kind"], item["elements"][0] if item.get("elements") else "")
        if key not in found:
            found[key] = {"widths": [], "line": f"{extra}{short(item)}"}
        if width not in found[key]["widths"]:
            found[key]["widths"].append(width)

    for base in sorted(out.glob("*.json")):
        if base.stem.endswith(("-stress", "-interact")):
            continue
        report = json.loads(base.read_text())
        page, width = pathlib.Path(report["url"]).name or report["url"], report["width"]
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
    lines = {"F": [], "W": [], "S": []}
    for (page, severity, _, _), value in found.items():
        widths = "/".join(f"{w}px" for w in sorted(value["widths"]))
        lines[severity].append(f"{severity} {page} @ {widths} {value['line']}")
    return lines["F"], lines["W"] + lines["S"]


def signature(files):
    return hashlib.sha256("".join(f"{f}:{os.stat(f).st_mtime_ns}:{os.stat(f).st_size}" for f in files).encode()).hexdigest()


def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    transcript = payload.get("transcript_path")
    cwd = payload.get("cwd") or os.getcwd()
    if not transcript or not os.path.exists(transcript):
        return 0
    state_file = pathlib.Path(tempfile.gettempdir()) / f"ui-stop-{payload.get('session_id') or pathlib.Path(transcript).stem}.json"
    state = json.loads(state_file.read_text()) if state_file.exists() else {"rounds": 0, "signature": ""}
    try:
        files = changed_files(transcript, cwd)
        if not files or state["rounds"] >= ROUNDS or signature(files) == state["signature"]:
            return 0
        state["signature"] = signature(files)
        pages = pages_for(files, cwd)
        found = lint(files, cwd)
        fails, others = measure(pages, cwd) if pages else ([], [])
    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
        return 0
    first = state["rounds"] == 0
    state["rounds"] += 1
    state_file.write_text(json.dumps(state))
    if not pages:
        if not first or payload.get("stop_hook_active") or measured_after_edit(transcript, cwd):
            return 0
        shown = "\n".join(f"- {f}" for f in files[:20])
        reason = (
            "You changed UI files, and the hook found no page to measure:\n"
            f"{shown}\n\n"
            "Load the `ui-check` skill and measure every page that uses these files with `--stress --interact`. "
            "To let the hook measure by itself next time, add a line `ui-check: <url or file> ...` to DESIGN.md. "
            "If no page can render, say so in your report and do not say that the UI is correct."
        )
        if found:
            reason += f"\n\nslop-lint on these files:\n{found}"
        json.dump({"decision": "block", "reason": reason}, sys.stdout)
        return 0
    if not fails and not (first and (others or found)):
        return 0
    lines = (fails + others)[:30]
    more = len(fails) + len(others) - len(lines)
    reason = (
        "The ui-check hook measured the pages that use the files you changed, with longer text, keyboard focus, hover and open menus:\n"
        + "\n".join(f"- {p}" for p in pages) + "\n\n"
        + "\n".join(lines) + (f"\n... {more} more" if more > 0 else "") + "\n\n"
        "Fix each F line. Fix each W and S line, or tell the user why the project's rules allow it. "
        "Fix the cause in the shared style when the same problem is on several pages. Do not remove content to make a check pass."
    )
    if found:
        reason += f"\n\nslop-lint on the changed files:\n{found}"
    json.dump({"decision": "block", "reason": reason}, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
