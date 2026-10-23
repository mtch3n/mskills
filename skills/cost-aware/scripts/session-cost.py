#!/usr/bin/env python3
import argparse
import json
import pathlib
import re
import sys

VERSION = 1
WAIT_TOOLS = {"Monitor", "TaskOutput", "BashOutput"}
WAIT_COMMAND = re.compile(r"\b(sleep|wait)\b|\bwatch\b|--watch\b")
TOKEN_KEYS = ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens", "output_tokens")
CONTEXT_WARN = 150_000
IMAGE_WARN = 10
WAIT_WARN = 10


def records(path):
    with open(path, encoding="utf-8", errors="replace") as handle:
        for line in handle:
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def measure(path):
    seen = set()
    totals = dict.fromkeys(TOKEN_KEYS, 0)
    result = {"turns": 0, "peak_context": 0, "images": 0, "wait_calls": 0, "tool_calls": 0, "unknown_usage": 0}
    for record in records(path):
        message = record.get("message")
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        blocks = content if isinstance(content, list) else []
        if record.get("type") == "assistant":
            key = message.get("id") or record.get("uuid")
            if key not in seen:
                seen.add(key)
                result["turns"] += 1
                usage = message.get("usage")
                if not isinstance(usage, dict):
                    result["unknown_usage"] += 1
                else:
                    for name in TOKEN_KEYS:
                        totals[name] += usage.get(name) or 0
                    context = sum(usage.get(name) or 0 for name in TOKEN_KEYS[:3])
                    result["peak_context"] = max(result["peak_context"], context)
            for block in blocks:
                if not isinstance(block, dict) or block.get("type") != "tool_use":
                    continue
                result["tool_calls"] += 1
                tool_input = block.get("input") or {}
                command = tool_input.get("command", "") if isinstance(tool_input, dict) else ""
                if block.get("name") in WAIT_TOOLS or WAIT_COMMAND.search(command or ""):
                    result["wait_calls"] += 1
        elif record.get("type") == "user":
            for block in blocks:
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    inner = block.get("content")
                    if isinstance(inner, list):
                        result["images"] += sum(1 for item in inner if isinstance(item, dict) and item.get("type") == "image")
    result.update(totals)
    return result


def warnings(result):
    found = []
    if result["peak_context"] > CONTEXT_WARN:
        found.append(f"peak context {result['peak_context']:,} > {CONTEXT_WARN:,}: hand off or move reading to a subagent")
    if result["images"] > IMAGE_WARN:
        found.append(f"{result['images']} images in context: let a subagent read them")
    if result["wait_calls"] > WAIT_WARN:
        found.append(f"{result['wait_calls']} wait calls: run it in the background and wait for one notification")
    if result["unknown_usage"]:
        found.append(f"{result['unknown_usage']} turns had no usage data")
    return found


def combine(key, results):
    values = [item[key] for item in results]
    if key == "peak_context":
        return max(values, default=0)
    return sum(values)


def subagent_files(path):
    folder = path.with_suffix("") / "subagents"
    return sorted(folder.glob("*.jsonl")) if folder.is_dir() else []


def main():
    parser = argparse.ArgumentParser(description="Measure the token cost of a Claude Code session transcript.")
    parser.add_argument("path", type=pathlib.Path, help="session .jsonl file")
    parser.add_argument("--json", action="store_true", help="print a versioned JSON report")
    args = parser.parse_args()
    main_result = measure(args.path)
    subagents = [measure(item) for item in subagent_files(args.path)]
    report = {
        "version": VERSION,
        "session": args.path.name,
        "main": main_result,
        "subagents": {"count": len(subagents), **{key: combine(key, subagents) for key in main_result}},
        "warnings": warnings(main_result),
    }
    if args.json:
        print(json.dumps(report, indent=2))
        return
    for label in ("main", "subagents"):
        part = report[label]
        print(
            f"{label}: {part['turns']} turns, peak context {part['peak_context']:,}, "
            f"cache read {part['cache_read_input_tokens']:,}, cache write {part['cache_creation_input_tokens']:,}, "
            f"input {part['input_tokens']:,}, output {part['output_tokens']:,}, "
            f"{part['images']} images, {part['wait_calls']} wait calls, {part['tool_calls']} tool calls"
        )
    for line in report["warnings"]:
        print(f"warn: {line}")


if __name__ == "__main__":
    sys.exit(main())
