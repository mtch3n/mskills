#!/usr/bin/env python3
import json
import re
import sys

CORRECTION = re.compile(
    r"\b(again|still|i (?:said|told you|asked)|already (?:said|told)|not what i|why (?:did|do|is|are) |stop |don'?t|do not|never|wrong|ugly|weird|messy|broken|"
    r"looks? (?:bad|off|wrong|weird|cheap|generic)|doesn'?t (?:line up|align|match|fit)|not (?:aligned|centered|centred|consistent)|misaligned|inconsistent|"
    r"too (?:big|small|much|many|wide|narrow|tight|close|far)|ai slop|slop|uneven|is gone|are gone|disappear\w*|cut off|overlap\w*|can'?t see|not visible|squished|cramped|off-center|off center)",
    re.I,
)
UI = re.compile(
    r"\b(ui|ux|css|layout|page|screen|button|card|table|header|footer|sidebar|navbar|modal|dialog|dropdown|badge|pill|icon|font|colou?r|"
    r"padding|margin|spacing|gap|align\w*|border|radius|shadow|gradient|design|pixel|\d+px|mobile|responsive|tooltip|looks?)\b",
    re.I,
)
COPY = re.compile(r"\b(too verbose|verbose|wordy|chatty|not useful|filler|remove (?:this|the|that) (?:text|sentence|line|subtitle|description|hint)|too (?:much|many) (?:text|words)|less text|like a text ?book)\b", re.I)
CONTEXT = (
    "The user corrects a UI result. Do these steps before you change code:\n"
    "1. Write the correction as a rule in the project's design rules file (DESIGN.md, or the UI section of CLAUDE.md or AGENTS.md). "
    "Use the user's words. If the rule is already there, the last change broke it: say so.\n"
    "2. Load the `ui-antislop` skill. Measure the pages before the change with `--out <dir>/before`.\n"
    "3. Find every instance of the problem on every page, not only the instance that the user named.\n"
    "4. Change only what the user named. After the change, measure with `--baseline <dir>/before` and undo each change that is not part of the task."
)

COPY_CONTEXT = (
    "\n5. The correction is about the words. Remove each sentence that does not help the next action or prevent a mistake. "
    "Do not reword it to keep it. Search every screen for the same kind of text, and check with `ui-antislop` (`helper-text`, `restates`, `filler`, `long-label`, `chatty`)."
)


NOT_USER = re.compile(r"<agent-message\b|<task-notification>|\[Subagent hand-back\]|^Another Claude session sent a message|^The \w+ plugin sent a message|<ostia-bus-messages>")


def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    prompt = payload.get("prompt") or ""
    if NOT_USER.search(prompt):
        return 0
    copy = bool(COPY.search(prompt))
    if not (copy or (CORRECTION.search(prompt) and UI.search(prompt))):
        return 0
    context = CONTEXT + (COPY_CONTEXT if copy else "")
    json.dump({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": context}}, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
