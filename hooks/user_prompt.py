import re

NOT_USER = re.compile(
    r"<agent-message\b|<task-notification>|\[Subagent hand-back\]|^\s*Another Claude session sent a message|^\s*The \w+ plugin sent a message"
    r"|\bostia bus: \d+ messages? from other panes|<message id=|^\s*You are (?:looking|checking|taking|reviewing|working|a |an )|^\s*Read and follow \S+"
)
PASTE = re.compile(r"<pasted_content\b.*?</pasted_content>", re.S)


def own_words(prompt):
    if NOT_USER.search(prompt):
        return ""
    return PASTE.sub(" ", prompt)
