#!/usr/bin/env python3
import json
import pathlib
import subprocess
import sys

UI = (".css", ".scss", ".sass", ".less", ".html", ".htm", ".jsx", ".tsx", ".vue", ".svelte", ".astro", ".mdx")
LINT = pathlib.Path(__file__).resolve().parent.parent / "skills" / "ui-antislop" / "scripts" / "slop-lint.py"


def written(path, data):
    text = pathlib.Path(path).read_text(errors="replace")
    if data.get("content") is not None:
        return set(range(1, text.count("\n") + 2))
    numbers = set()
    for part in [data.get("new_string") or ""] + [edit.get("new_string") or "" for edit in data.get("edits") or []]:
        start = text.find(part) if part.strip() else -1
        while start != -1:
            first = text.count("\n", 0, start) + 1
            numbers.update(range(first, first + part.count("\n") + 1))
            start = text.find(part, start + 1)
    return numbers


def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    data = payload.get("tool_input") or {}
    path = data.get("file_path") or ""
    if not path.endswith(UI) or not pathlib.Path(path).is_file():
        return 0
    if subprocess.run(["git", "-C", str(pathlib.Path(path).parent), "rev-parse"], capture_output=True).returncode != 0:
        return 0
    lines = written(path, data)
    if not lines:
        return 0
    try:
        result = subprocess.run([sys.executable, "-I", str(LINT), path], capture_output=True, text=True, cwd=payload.get("cwd") or None, timeout=20)
    except subprocess.SubprocessError:
        return 0
    found = []
    for line in result.stdout.splitlines()[:-1]:
        place = line.split(": ", 1)[0]
        number = place.rsplit(":", 1)[-1]
        if (number.isdigit() and int(number) in lines) or ": shadcn-file: " in line:
            found.append(line)
    if not found:
        return 0
    context = "slop-lint found these in the lines you just wrote. Fix them, or tell the user why the project needs them:\n" + "\n".join(found[:15])
    json.dump({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": context}}, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
