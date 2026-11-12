#!/usr/bin/env python3
import json
import re
import sys

ASK = re.compile(
    r"(?i)\b(?:want|would you like|do you want)\s+me\s+to\b"
    r"|\b(?:should|shall)\s+(?:i|we)\b"
    r"|\blet me know (?:if|whether|which|what|how)\b"
    r"|\b(?:if you(?:'d)? (?:like|want)|if that works),? i(?:'ll| can| will)\b"
    r"|\bi can (?:also|then|next)\b"
    r"|\b(?:which|what) (?:one|option|approach|way) (?:do|would|should) (?:you|we)\b"
    r"|\bready (?:for me )?to (?:proceed|continue|start)\b"
    r"|要(?:我|不要我)|需要我|是否(?:要|需要)?(?:我|繼續|继续)|我可以(?:再|也|接著|接着)"
)
OUTWARD = re.compile(
    r"(?i)\b(?:push|merge|deploy|release|publish|send|email|post|comment on|delete|drop|remove|"
    r"rm\b|force|rotate|prod|production|pay|purchase|commit|tag|install on|restart|reboot|"
    r"firewall|secret|password|credential|token|key vault)"
    r"|推送|合併|合并|部署|發布|发布|刪除|删除|生產|生产|密碼|密码|提交"
)
REASON = (
    "Your reply ends by asking the user about work. Check it before you stop. "
    "If the asked task is finished, remove the offer and stop; do not start work the user did not ask for. "
    "If work of the asked task is left and best practice decides it (in a legacy project, the existing pattern), "
    "say the choice in one line and continue. Ask only for a destructive or outward-facing action "
    "(push, merge, deploy, send, publish), money, secrets, shared infra, a product choice with no technical answer, "
    "or a fact only the user has. If you stop for one of these, name which one."
)


def last_paragraph(text):
    parts = [p.strip() for p in re.split(r"\n\s*\n", text or "") if p.strip()]
    return parts[-1] if parts else ""


def main():
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        return 0
    if not isinstance(payload, dict) or payload.get("stop_hook_active"):
        return 0
    tail = last_paragraph(payload.get("last_assistant_message"))
    if not ASK.search(tail) or OUTWARD.search(tail):
        return 0
    json.dump({"decision": "block", "reason": REASON}, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
