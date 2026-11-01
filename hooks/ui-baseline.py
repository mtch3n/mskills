#!/usr/bin/env python3
import importlib.util
import json
import os
import pathlib
import re
import sys
import tempfile

OPEN = re.compile(r"\b(?:polish|clean ?up|tidy|ship|launch|release|review|audit|ai[- ]?slop|slop|looks? (?:off|bad|wrong|cheap|generic|ugly|weird)|make it (?:look|feel)|improve the (?:ui|design|look|page|screen)|qa)\b", re.I)
UI = re.compile(r"\b(?:page|screen|ui|ux|design|layout|view|dashboard|site|website|form|table|modal|dialog|component)s?\b", re.I)
NOT_USER = re.compile(r"<agent-message\b|<task-notification>|\[Subagent hand-back\]|^Another Claude session sent a message|^The \w+ plugin sent a message")
LIMIT = 4

spec = importlib.util.spec_from_file_location("ui_measure", pathlib.Path(__file__).with_name("ui_measure.py"))
ui = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ui)


def words(text):
    return {w.lower() for w in re.findall(r"[A-Za-z][\w-]+", text)}


def named_pages(prompt, root):
    said = words(prompt)
    listed, _ = ui.listed_pages(root)
    candidates = [str(p) for p in ui.html_files(root)] + listed
    named = [p for p in candidates if pathlib.Path(p.rstrip("/")).stem.lower() in said - {"index", "page", "app"}]
    if named:
        return list(dict.fromkeys(named))[:LIMIT]
    return listed[:LIMIT]


def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    prompt = payload.get("prompt") or ""
    if NOT_USER.search(prompt):
        return 0
    state = pathlib.Path(tempfile.gettempdir()) / f"ui-baseline-{payload.get('session_id') or 'session'}.json"
    state.unlink(missing_ok=True)
    if not (OPEN.search(prompt) and UI.search(prompt)):
        return 0
    cwd = payload.get("cwd") or os.getcwd()
    root = ui.root_of(cwd)
    pages = named_pages(prompt, root)
    if not pages:
        return 0
    lines = [text for _, _, text in ui.measure(pages, cwd, ["--interact"], 90)]
    state.write_text(json.dumps({"pages": pages, "shown": lines}))
    found = ui.lint(ui.stylesheets(pages) + [p for p in pages if pathlib.Path(p).is_file()], cwd)
    if not lines and not found:
        return 0
    context = (
        "Before you start, the ui-antislop hook measured the pages of this request:\n"
        + "\n".join(f"- {p}" for p in pages) + "\n\n"
        + "\n".join(lines[:30]) + (f"\n... {len(lines) - 30} more" if len(lines) > 30 else "")
        + (f"\n\nslop-lint on these pages and their styles:\n{found}" if found else "")
        + "\n\nThese problems are already on the page. Fix them as part of this task, in one pass. "
        "This list is not complete: a tool measures only some problems. Read the page and its styles yourself, as you do with no list, "
        "and fix the other problems that you find, for example parts that do not line up or one component with different styles. "
        "Fix each F line. Fix each W line, or tell the user why the project's rules allow it. An S line is a question: remove the item only if it is decoration that no rule asks for. "
        "Do not remove content, data or controls to make a check pass. "
        "The text after @ is the CSS rule that sets the value. When you stop, the hook measures again and shows only new F lines."
    )
    json.dump({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": context}}, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
