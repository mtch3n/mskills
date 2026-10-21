#!/usr/bin/env python3
import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

PROJECTS = Path.home() / ".claude" / "projects"
AGENT_TEXT_LIMIT = 1500
RUN_INPUT_LIMIT = 200
RUN_RESULT_LIMIT = 160


def project_dir(path):
    return PROJECTS / re.sub(r"[^A-Za-z0-9]", "-", os.path.abspath(path))


FIND_LIMIT = 15
SEARCH_MARKERS = ('"kind":"human"', '"type":"assistant"')
SNIPPET_LIMIT = 120


def scope(project, everything):
    if everything:
        return [d for d in PROJECTS.iterdir() if d.is_dir()]
    base = project_dir(project).name
    return [d for d in PROJECTS.glob(base + "*") if d.name == base or d.name.startswith(base + "--claude-worktrees-")]


def sessions(folders):
    found = [p for d in folders for p in d.glob("*.jsonl")]
    return sorted(found, key=lambda p: p.stat().st_mtime, reverse=True)


def by_id(prefix):
    return sorted(PROJECTS.glob(f"*/{prefix}*.jsonl"), key=lambda p: p.stat().st_mtime)


def records(path):
    with path.open() as f:
        for line in f:
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def clip(text, limit):
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def clock(record):
    stamp = record.get("timestamp")
    if not stamp:
        return "--:--"
    return datetime.fromisoformat(stamp.replace("Z", "+00:00")).astimezone().strftime("%m-%d %H:%M")


def text_of(content):
    if isinstance(content, str):
        return content
    return "\n".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")


def last_line(content):
    lines = [l for l in text_of(content).splitlines() if l.strip()]
    return lines[-1] if lines else ""


def describe_call(block):
    name, args = block["name"], block.get("input") or {}
    if name == "Bash":
        summary = args.get("description") or ""
        return name, clip(f"{summary}: {args.get('command', '')}" if summary else args.get("command", ""), RUN_INPUT_LIMIT)
    for key in ("file_path", "path", "description", "skill", "query", "pattern"):
        if key in args:
            return name, clip(args[key], RUN_INPUT_LIMIT)
    return name, clip(json.dumps(args), RUN_INPUT_LIMIT)


def is_human(record):
    return (record.get("origin") or {}).get("kind") == "human"


def timeline(path):
    calls, out, title, first, last, branch, cwd = {}, [], "", None, None, "", ""
    for r in records(path):
        if r.get("isSidechain"):
            continue
        kind = r.get("type")
        if kind == "ai-title":
            title = r.get("aiTitle", title)
            continue
        if r.get("timestamp"):
            first = first or r
            last = r
        branch = r.get("gitBranch") or branch
        cwd = r.get("cwd") or cwd
        if kind == "attachment":
            a = r.get("attachment") or {}
            if a.get("type") == "queued_command" and (a.get("origin") or {}).get("kind") == "human":
                out.append(f"[{clock(a)}] USER: {text_of(a.get('prompt', ''))}")
            continue
        if kind == "user" and not r.get("isMeta"):
            content = r["message"]["content"]
            if isinstance(content, str):
                if is_human(r):
                    out.append(f"[{clock(r)}] USER: {content}")
                continue
            for b in content:
                if b.get("type") != "tool_result":
                    continue
                name, summary = calls.get(b.get("tool_use_id"), ("?", ""))
                answers = (r.get("toolUseResult") or {}).get("answers") if isinstance(r.get("toolUseResult"), dict) else None
                if name == "AskUserQuestion" and answers:
                    for q, a in answers.items():
                        out.append(f"[{clock(r)}] USER ANSWER: {q} → {a}")
                    continue
                status = "error" if b.get("is_error") else "ok"
                tail = clip(last_line(b.get("content", "")), RUN_RESULT_LIMIT)
                out.append(f"[{clock(r)}] RUN {name}: {summary} → {status}" + (f" | {tail}" if tail else ""))
        elif kind == "assistant":
            for b in r["message"]["content"]:
                if b.get("type") == "text" and b["text"].strip():
                    out.append(f"[{clock(r)}] AGENT: {clip(b['text'], AGENT_TEXT_LIMIT)}")
                elif b.get("type") == "tool_use":
                    calls[b["id"]] = describe_call(b)
    span = f"{clock(first)} → {clock(last)}" if first else "empty"
    header = f"# session {path.stem} | {title or 'untitled'} | {span} | cwd {cwd or '?'} | branch {branch or '?'}"
    return [header, *out]


def searchable(record):
    kind = record.get("type")
    if kind == "user" and is_human(record) and isinstance(record["message"]["content"], str):
        return "USER", record["message"]["content"]
    if kind == "attachment":
        a = record.get("attachment") or {}
        if a.get("type") == "queued_command" and (a.get("origin") or {}).get("kind") == "human":
            return "USER", text_of(a.get("prompt", ""))
    if kind == "assistant" and not record.get("isSidechain"):
        return "AGENT", text_of(record["message"]["content"])
    return None, ""


def score(path, terms):
    hits, matched, title, cwd, snippet = 0, set(), "", "", ""
    with path.open() as f:
        for line in f:
            is_title = '"type":"ai-title"' in line
            if not is_title and not any(m in line for m in SEARCH_MARKERS):
                continue
            low = line.lower()
            if not is_title and not any(t in low for t in terms):
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if is_title:
                title = r.get("aiTitle", title)
            cwd = cwd or r.get("cwd", "")
            who, text = searchable(r)
            found = {t for t in terms if t in text.lower()}
            if not who or not found:
                continue
            hits += 1
            matched |= found
            if who == "USER" and not snippet:
                snippet = clip(text, SNIPPET_LIMIT)
    return hits, matched, title, cwd, snippet


def find(paths, terms, current):
    results = []
    for p in paths:
        hits, matched, title, cwd, snippet = score(p, terms)
        if hits:
            results.append((len(matched), hits, p, title, cwd, snippet))
    results.sort(key=lambda x: (x[0], x[1]), reverse=True)
    for words, hits, p, title, cwd, snippet in results[:FIND_LIMIT]:
        stamp = datetime.fromtimestamp(p.stat().st_mtime).strftime("%m-%d %H:%M")
        mark = " (this session)" if p.stem == current else ""
        print(f"{p.stem}  {stamp}{mark}  {hits} hits, {words}/{len(terms)} words  {cwd}  | {title or 'untitled'} | {snippet}")
    if len(results) > FIND_LIMIT:
        print(f"… {len(results) - FIND_LIMIT} more sessions with fewer hits")


def first_prompt(path):
    for r in records(path):
        if r.get("type") == "user" and is_human(r) and isinstance(r["message"]["content"], str):
            return clip(r["message"]["content"], 100)
    return ""


def main():
    parser = argparse.ArgumentParser(description="Find past Claude Code sessions and print them as compact timelines.")
    parser.add_argument("--project", default=os.getcwd(), help="folder the sessions ran in, its worktrees included (default: cwd)")
    parser.add_argument("--all", action="store_true", help="search every project, not just --project")
    parser.add_argument("--find", metavar="WORDS", help="rank sessions by how often user and agent messages mention these words")
    parser.add_argument("--list", action="store_true", help="list recent sessions and exit")
    parser.add_argument("--session", nargs="+", metavar="ID", help="print these sessions (ids or prefixes, any project), oldest first")
    parser.add_argument("--count", type=int, default=1, help="without --session: how many recent sessions other than this one (default: 1)")
    args = parser.parse_args()

    current = os.environ.get("CLAUDE_CODE_SESSION_ID")
    if args.session:
        chosen = sorted({p for prefix in args.session for p in by_id(prefix)[:1]}, key=lambda p: p.stat().st_mtime)
        missing = [x for x in args.session if not by_id(x)]
        if missing:
            print(f"no session {', '.join(missing)} under {PROJECTS}", file=sys.stderr)
            return 1
    else:
        folders = scope(args.project, args.all)
        if not folders:
            print(f"no sessions recorded for {args.project}", file=sys.stderr)
            return 1
        found = sessions(folders)
        if args.find:
            find(found, [t.lower() for t in args.find.split()], current)
            return 0
        if args.list:
            for p in found[:20]:
                stamp = datetime.fromtimestamp(p.stat().st_mtime).strftime("%m-%d %H:%M")
                mark = " (this session)" if p.stem == current else ""
                print(f"{p.stem}  {stamp}{mark}  {first_prompt(p)}")
            return 0
        chosen = list(reversed([p for p in found if p.stem != current][: args.count]))
    for p in chosen:
        print("\n".join(timeline(p)))
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
