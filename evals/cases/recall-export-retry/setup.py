import json
import os
import pathlib
import re
import uuid
from datetime import datetime, timedelta, timezone

pathlib.Path("export.py").write_text('''import random
import time

MAX_ATTEMPTS = 5


class ExportFailed(Exception):
    pass


def run_export(send, sleep=time.sleep):
    for attempt in range(1, MAX_ATTEMPTS + 1):
        status = send()
        if status < 400:
            return status
        if status < 500 or attempt == MAX_ATTEMPTS:
            raise ExportFailed(status)
        sleep(2 ** attempt + random.uniform(0, 1))
''')
pathlib.Path("csvexport.py").write_text('''import argparse
import csv
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--delimiter", default=",")
    args = parser.parse_args()
    csv.writer(sys.stdout, delimiter=args.delimiter).writerow(["id", "total"])


if __name__ == "__main__":
    main()
''')
pathlib.Path("README.md").write_text("# jobs\n\nThe nightly export and its tools.\n")

cwd = os.getcwd()
folder = pathlib.Path(os.environ["CLAUDE_CONFIG_DIR"]) / "projects" / re.sub(r"[^A-Za-z0-9]", "-", os.path.abspath(cwd))
folder.mkdir(parents=True, exist_ok=True)


def session(start, title, steps):
    sid = str(uuid.uuid4())
    moment = start
    lines = [{"type": "ai-title", "aiTitle": title, "sessionId": sid}]
    base = {"sessionId": sid, "cwd": cwd, "gitBranch": "main"}
    for step in steps:
        moment += timedelta(minutes=3)
        stamp = moment.isoformat().replace("+00:00", "Z")
        if step[0] == "user":
            lines.append({**base, "type": "user", "timestamp": stamp, "origin": {"kind": "human"}, "message": {"role": "user", "content": step[1]}})
        elif step[0] == "agent":
            lines.append({**base, "type": "assistant", "timestamp": stamp, "message": {"role": "assistant", "content": [{"type": "text", "text": step[1]}]}})
        else:
            _, name, tool_input, result = step
            call = "toolu_" + uuid.uuid4().hex[:20]
            lines.append({**base, "type": "assistant", "timestamp": stamp, "message": {"role": "assistant", "content": [{"type": "tool_use", "id": call, "name": name, "input": tool_input}]}})
            lines.append({**base, "type": "user", "timestamp": stamp, "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": call, "content": result}]}})
    path = folder / f"{sid}.jsonl"
    path.write_text("".join(json.dumps(line, separators=(",", ":")) + "\n" for line in lines))
    os.utime(path, (moment.timestamp(), moment.timestamp()))


def noise(count, seed):
    steps = []
    for index in range(count):
        lines = [f"2026-11-0{seed}T0{index % 10}:{index:02d}:{n % 60:02d}Z INFO [export] chunk {n} written, {(n * 37 + index) % 900 + 100} rows, {(n * 13) % 400 + 20} ms" for n in range(320)]
        steps.append(("tool", "Bash", {"command": f"tail -n 320 logs/export-{seed}-{index}.log", "description": "Read the export log"}, "\n".join(lines)))
    return steps


day = lambda d: datetime(2026, 11, d, 9, 0, tzinfo=timezone.utc)
session(day(1), "Retry for nightly export", [
    ("user", "The nightly export fails on flaky 503s. Add a retry to run_export in export.py: at most 3 attempts, and never retry a 4xx."),
    *noise(12, 1),
    ("tool", "Edit", {"file_path": f"{cwd}/export.py", "old_string": "status = send()", "new_string": "for attempt in range(1, MAX_ATTEMPTS + 1):"}, "The file export.py has been updated successfully."),
    ("tool", "Bash", {"command": "python3 -m pytest -q", "description": "Run tests"}, "3 passed in 0.02s"),
    ("agent", "Done. run_export now retries 5xx responses up to 3 attempts with exponential backoff, and a 4xx fails at once. The tests pass."),
    ("user", "also fix the typo in the README, it says nighly"),
    ("agent", "Fixed the typo in README.md."),
])
session(day(2), "Dockerfile cleanup", [
    ("user", "Make the Dockerfile smaller, use the slim python image."),
    *noise(8, 2),
    ("agent", "Switched the base image to python:3.13-slim."),
])
session(day(3), "Export retry changes", [
    ("user", "About the export retry: make it 5 attempts, and log each retry with the attempt number so on-call can see it."),
    *noise(12, 3),
    ("tool", "Edit", {"file_path": f"{cwd}/export.py", "old_string": "MAX_ATTEMPTS = 3", "new_string": "MAX_ATTEMPTS = 5"}, "The file export.py has been updated successfully."),
    ("agent", "Updated: MAX_ATTEMPTS is now 5 and every retry is logged with its attempt number. I also added a random jitter of 0 to 1 second to the backoff so that parallel jobs do not retry at the same moment."),
])
session(day(5), "CSV delimiter option", [
    ("user", "Add a --delimiter option to csvexport.py, default comma."),
    *noise(12, 5),
    ("tool", "Edit", {"file_path": f"{cwd}/csvexport.py", "old_string": "parser = argparse.ArgumentParser()", "new_string": "parser.add_argument(\"--delimiter\", default=\",\")"}, "The file csvexport.py has been updated successfully."),
    ("agent", "Added --delimiter with a comma default."),
    ("user", "One more thing on the export retry: keep it as it is for now, but do not ship it until finance has reviewed the no-retry-on-4xx rule."),
    ("agent", "Understood. The retry change waits for the finance review of the 4xx rule before it ships."),
])
