#!/usr/bin/env python3
import json
import sys

REASON = (
    "Set `model` on every subagent. Use haiku to scan, search, fetch, read, sort or count. "
    "Use sonnet to build or edit code. Use opus only for judgment: design, review, a hard diagnosis. "
    "A fork takes no model."
)


def main():
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        return 0
    if not isinstance(payload, dict) or payload.get("tool_name") not in ("Agent", "Task"):
        return 0
    data = payload.get("tool_input") or {}
    if data.get("subagent_type") == "fork" or data.get("model"):
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
