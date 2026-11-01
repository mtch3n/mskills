#!/usr/bin/env python3
import json
import pathlib
import subprocess
import sys

UI = (".css", ".scss", ".sass", ".less", ".html", ".htm", ".jsx", ".tsx", ".vue", ".svelte", ".astro", ".mdx")
LINT = pathlib.Path(__file__).resolve().parent.parent / "skills" / "ui-check" / "scripts" / "slop-lint.py"


def written(data):
    parts = [data.get("new_string") or "", data.get("content") or ""]
    parts += [edit.get("new_string") or "" for edit in data.get("edits") or []]
    return {line.strip() for part in parts for line in part.splitlines() if line.strip()}


def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    data = payload.get("tool_input") or {}
    path = data.get("file_path") or ""
    if not path.endswith(UI) or not pathlib.Path(path).is_file():
        return 0
    lines = {line[:120] for line in written(data)}
    if not lines:
        return 0
    try:
        result = subprocess.run([sys.executable, "-I", str(LINT), path], capture_output=True, text=True, cwd=payload.get("cwd") or None, timeout=20)
    except subprocess.SubprocessError:
        return 0
    found = []
    for line in result.stdout.splitlines()[:-1]:
        text = line.split(" | ", 1)[1] if " | " in line else ""
        if text in lines or ": shadcn-file: " in line or ": data-table: " in line:
            found.append(line)
    allowed = [line for line in result.stdout.splitlines() if line.startswith("allowed by DESIGN.md")]
    if not found:
        return 0
    context = "slop-lint found these in the lines you just wrote. Fix them, or follow the project's rules if they allow it:\n" + "\n".join(found[:15] + allowed)
    json.dump({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": context}}, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
