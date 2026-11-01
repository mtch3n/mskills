#!/usr/bin/env python3
import datetime
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import importlib.util

UI = (".css", ".scss", ".sass", ".less", ".html", ".htm", ".jsx", ".tsx", ".vue", ".svelte", ".astro", ".mdx")
UI_PATH = re.compile(r"[\w./~@+-]+(?:" + "|".join(re.escape(e) for e in UI) + r")\b")
WRITES = re.compile(r"\bsed\s+-i|\bperl\s+-p?i|>|\btee\b|\bpython3?\b|\bmv\b|\bcp\b|\bpatch\b|\bgit\s+apply\b")
MEASURE = re.compile(r"ui-check\.py|probe\.js")
EDIT_TOOLS = {"Edit", "Write", "MultiEdit"}
ROUNDS = 3
FIXTURE = re.compile(r"/(tests?|__tests__|fixtures?|__fixtures__|evals)/")
ROUTES = [re.compile(p) for p in [r"^(?:src/)?app/(.*?)/?page\.(?:tsx|jsx|ts|js|mdx)$", r"^(?:src/)?pages/(.*?)\.(?:tsx|jsx|astro|vue|svelte|mdx)$", r"^src/routes/(.*?)/?\+page\.svelte$"]]

spec = importlib.util.spec_from_file_location("ui_measure", pathlib.Path(__file__).with_name("ui_measure.py"))
ui = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ui)


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
    root = ui.root_of(cwd).resolve()
    return sorted(str(p) for p in files if p.is_file() and p.resolve().is_relative_to(root) and p.stat().st_mtime >= start and not FIXTURE.search(p.as_posix()))


def measured_after_edit(transcript, cwd):
    last_edit = last_measure = -1
    for index, event in enumerate(events(transcript)):
        for use in tool_uses(event):
            if use.get("name") == "Bash" and MEASURE.search((use.get("input") or {}).get("command") or ""):
                last_measure = index
            if touched(use, cwd):
                last_edit = index
    return last_measure > last_edit


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


def pages_for(files, cwd, named):
    root = ui.root_of(cwd)
    listed, base = ui.listed_pages(root)
    direct = [f for f in files if f.endswith((".html", ".htm"))]
    shared = []
    assets = {str(pathlib.Path(f).resolve()) for f in files if not f.endswith((".html", ".htm"))}
    if assets:
        for path in ui.html_files(root):
            if str(path) not in direct and path.is_file() and not FIXTURE.search(path.as_posix()) and assets & ui.references(path):
                shared.append(str(path))
    routes = [r for r in (route_of(f, root) for f in files) if r is not None]
    server = base or ((routes or not (direct or shared)) and ui.dev_server())
    if server:
        direct += [server + r for r in dict.fromkeys(routes or ["/"])]
    shared += [item for item in listed if not (base and item.rstrip("/") == base)]
    direct += [p for p in named if p not in direct]
    pages = list(dict.fromkeys(direct + shared))[:6]
    return pages, {ui.label(p) for p in direct}


def signature(files):
    return hashlib.sha256("".join(f"{f}:{os.stat(f).st_mtime_ns}:{os.stat(f).st_size}" for f in files).encode()).hexdigest()


def last_prompt(transcript):
    last = None
    for event in events(transcript):
        content = (event.get("message") or {}).get("content")
        if event.get("type") == "user" and not event.get("isMeta") and (isinstance(content, str) or any(isinstance(c, dict) and c.get("type") == "text" for c in content or [])):
            last = event.get("uuid") or event.get("timestamp")
    return last


def baseline(session):
    path = pathlib.Path(tempfile.gettempdir()) / f"ui-baseline-{session}.json"
    return json.loads(path.read_text()) if path.exists() else {}


def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    transcript = payload.get("transcript_path")
    cwd = payload.get("cwd") or os.getcwd()
    if not transcript or not os.path.exists(transcript):
        return 0
    session = payload.get("session_id") or pathlib.Path(transcript).stem
    state_file = pathlib.Path(tempfile.gettempdir()) / f"ui-stop-{session}.json"
    state = json.loads(state_file.read_text()) if state_file.exists() else {}
    prompt = last_prompt(transcript)
    if not state or state.get("prompt") != prompt:
        state = {"prompt": prompt, "rounds": 0, "signature": "", "shown": baseline(session).get("shown", [])}
    try:
        files = changed_files(transcript, cwd)
        if not files or state["rounds"] >= ROUNDS or signature(files) == state["signature"]:
            return 0
        state["signature"] = signature(files)
        pages, direct = pages_for(files, cwd, baseline(session).get("pages", []))
        found = ui.lint(files, cwd)
        lines = ui.measure(pages, cwd, ["--stress", "--interact"], 270) if pages else []
    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
        return 0
    first = state["rounds"] == 0
    state["rounds"] += 1
    if not pages:
        state_file.write_text(json.dumps(state))
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
    kept = [text for page, severity, text in lines if severity == "F" or page in direct]
    fails = [text for text in kept if text.startswith("F ")]
    new = [text for text in kept if text not in state["shown"]]
    lint_new = found and found not in state["shown"]
    state["shown"] += new + ([found] if lint_new else [])
    state_file.write_text(json.dumps(state))
    if not fails and not new and not lint_new:
        return 0
    shown = kept[:30]
    more = len(kept) - len(shown)
    reason = (
        "The ui-check hook measured the pages that use the files you changed, with longer text, keyboard focus, hover and open menus:\n"
        + "\n".join(f"- {p}" for p in pages) + "\n\n"
        + "\n".join(shown) + (f"\n... {more} more" if more > 0 else "") + "\n\n"
        "Fix each F line. Fix each W line, or tell the user why the project's rules allow it. An S line is a question: remove the item only if it is decoration that no rule asks for. "
        "Do not remove content, data or controls to make a check pass. "
        "The text after @ is the CSS rule that sets the value. Fix the cause in the shared style when the same problem is on several pages. "
        "On a page that the user did not name, change only what an F line needs. "
        "If a page was not measured, say so in your report and do not say that it is correct."
    )
    if found and lint_new:
        reason += f"\n\nslop-lint on the changed files:\n{found}"
    json.dump({"decision": "block", "reason": reason}, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
