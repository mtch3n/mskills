import re


def read_whole_log(calls):
    for call in calls:
        tool_input = call["input"]
        if call["name"] == "Read" and str(tool_input.get("file_path", "")).endswith("app.log") and not tool_input.get("limit"):
            return True
        command = str(tool_input.get("command", "")) if call["name"] == "Bash" else ""
        if re.search(r"\bcat\s+\S*app\.log\s*($|;|&&)", command):
            return True
    return False


def grade(run):
    final = run.final.lower()
    grades = [
        {"name": "disk-full", "passed": bool(re.search(r"no space|disk.*(full|space)|/var/lib/jobs", final)), "weight": 1},
        {"name": "expired-cert", "passed": bool(re.search(r"certificate|cert\b|tls", final)), "weight": 1},
        {"name": "db-connections", "passed": bool(re.search(r"too many connections|connection limit|export_ro", final)), "weight": 1},
    ]
    verdict = run.judge(
        {"no-red-herring": "The answer does not present the es-2 search upstream timeout as a root cause of the nightly-export failure. Mentioning it as recovered noise is fine."},
        run.final,
    )["no-red-herring"]
    grades.append({"name": "no-red-herring", "passed": verdict["passed"], "weight": 1, "detail": verdict["reason"]})
    whole = read_whole_log(run.calls)
    grades.append({"name": "did-not-read-whole-log", "passed": not whole, "weight": 1, "metrics": {"read_whole_log": whole}})
    edited = any(call["name"] in ("Edit", "Write") for call in run.calls)
    grades.append({"name": "no-edits", "passed": not edited, "weight": 1})
    return grades
