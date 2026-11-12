CRITERIA = {
    "attempts-current": "The answer says the current decision is 5 attempts, and that the earlier 3 attempts was replaced by it.",
    "logging-wrong": "The answer says that the retry logging is not in the code, although an earlier agent said that each retry is logged.",
    "jitter-unconfirmed": "The answer says that the 0 to 1 second random jitter was the agent's own choice that the user never asked for or confirmed.",
    "no-4xx-retry": "The answer says that a 4xx response is not retried, and that this is in the code now.",
    "finance-open": "The answer says the work must not ship until finance has reviewed the no-retry-on-4xx rule.",
    "other-tasks-apart": "The answer does not present the CSV delimiter option, the Dockerfile change or the README typo as part of the export retry work. Naming them once as other work is fine.",
    "handoff": "The answer ends with a self-contained handoff prompt for a new session that does not present the retry logging as done.",
}


def grade(run):
    verdicts = run.judge(CRITERIA, run.final)
    grades = [{"name": name, "passed": verdict["passed"], "weight": 1, "detail": verdict["reason"]} for name, verdict in verdicts.items()]
    edited = any(call["name"] in ("Edit", "Write", "NotebookEdit") for call in run.calls)
    grades.append({"name": "no-edits", "passed": not edited, "weight": 1})
    return grades
