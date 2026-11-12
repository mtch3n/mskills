#!/usr/bin/env python3
import json
import pathlib
import re
import sys

REASON = (
    "Set `model` on every subagent. Use haiku to scan, search, fetch, read, sort or count. "
    "Use sonnet to build or edit code. Use opus only for judgment: design, review, a hard diagnosis. "
    "A fork takes no model."
)

AGENTS = pathlib.Path(__file__).resolve().parents[1] / "agents"


def sets_own_model(subagent_type):
    plugin, _, name = (subagent_type or "").partition(":")
    if plugin != "mskills" or not re.fullmatch(r"[\w-]+", name):
        return False
    path = AGENTS / f"{name}.md"
    if not path.is_file():
        return False
    header = path.read_text(errors="replace").split("---")
    return len(header) > 2 and re.search(r"^model:\s*\S", header[1], re.M) is not None


def main():
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        return 0
    if not isinstance(payload, dict) or payload.get("tool_name") not in ("Agent", "Task"):
        return 0
    data = payload.get("tool_input") or {}
    if data.get("subagent_type") == "fork" or data.get("model") or sets_own_model(data.get("subagent_type")):
        return 0
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": REASON,
            }
        },
        sys.stdout,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
