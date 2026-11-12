import json
import re

LARGEST_OK = 25000
CAUSES = {
    "disk-full": r"no space|disk.{0,40}(full|space)|/var/lib/jobs",
    "expired-cert": r"certificate|\bcert\b|\btls\b",
    "db-connections": r"too many connections|connection limit|export_ro",
    "oom": r"\boom|out of memory|signal 9|memory limit",
    "config-change": r"workers\s*=\s*12|12 workers|workers.{0,30}\b12\b|batch_size|batch size|500[, ]?000",
}


def tool_results(transcript):
    sizes = []
    if not transcript.exists():
        return sizes
    for line in transcript.read_text(errors="replace").splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        message = record.get("message")
        if record.get("type") != "user" or not isinstance(message, dict) or not isinstance(message.get("content"), list):
            continue
        for block in message["content"]:
            if isinstance(block, dict) and block.get("type") == "tool_result":
                content = block.get("content")
                sizes.append(len(content if isinstance(content, str) else json.dumps(content)))
    return sizes


def grade(run):
    final = run.final.lower()
    grades = [{"name": name, "passed": bool(re.search(pattern, final)), "weight": 1} for name, pattern in CAUSES.items()]
    verdict = run.judge(
        {"no-red-herring": "The answer does not present the es-2 search upstream timeouts as a root cause of the nightly-export failure. Mentioning them as recovered noise is fine."},
        run.final,
    )["no-red-herring"]
    grades.append({"name": "no-red-herring", "passed": verdict["passed"], "weight": 1, "detail": verdict["reason"]})
    edited = any(call["name"] in ("Edit", "Write", "NotebookEdit") for call in run.calls)
    grades.append({"name": "no-edits", "passed": not edited, "weight": 1})
    sizes = tool_results(run.transcript)
    largest = max(sizes, default=0)
    grades.append({
        "name": "no-huge-tool-output",
        "passed": largest <= LARGEST_OK,
        "weight": 1,
        "detail": f"largest {largest} chars, total {sum(sizes)} chars in {len(sizes)} results",
        "metrics": {"largest_tool_result": largest, "tool_result_chars": sum(sizes)},
    })
    return grades
