#!/usr/bin/env python3
import argparse
import concurrent.futures
import datetime
import importlib.util
import json
import os
import pathlib
import re
import shutil
import socket
import subprocess
import sys
import tempfile

EVALS = pathlib.Path(__file__).resolve().parent
REPO = EVALS.parent
SESSION_COST = REPO / "skills" / "cost-aware" / "scripts" / "session-cost.py"
DISABLE_INSTALLED = json.dumps({"enabledPlugins": {"mskills@mskills": False}})
JUDGE_MODEL = "sonnet"


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def config_dir():
    return pathlib.Path(os.environ.get("CLAUDE_CONFIG_DIR", pathlib.Path.home() / ".claude"))


def eval_config_dir():
    folder = pathlib.Path(tempfile.gettempdir()) / "mskills-eval-config"
    folder.mkdir(exist_ok=True)
    for entry in config_dir().iterdir():
        link = folder / entry.name
        if entry.name == "CLAUDE.md" or link.is_symlink() or link.exists():
            continue
        link.symlink_to(entry)
    return folder


def transcript_path(workdir, session_id):
    slug = re.sub(r"[^A-Za-z0-9]", "-", str(workdir))
    return config_dir() / "projects" / slug / f"{session_id}.jsonl"


EVAL_CONFIG = None


def free_port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def stop_leftovers(workdir, session):
    subprocess.run(["agent-browser", "--session", session, "close"], capture_output=True)
    for proc in pathlib.Path("/proc").iterdir():
        if not proc.name.isdigit():
            continue
        try:
            if pathlib.Path(os.readlink(proc / "cwd")).is_relative_to(workdir):
                os.kill(int(proc.name), 15)
        except OSError:
            continue


def claude(prompt, cwd, model, max_turns, timeout, plugin_dir=None):
    command = [
        "claude", "-p", prompt,
        "--model", model,
        "--max-turns", str(max_turns),
        "--output-format", "json",
        "--settings", DISABLE_INSTALLED,
        "--permission-mode", "bypassPermissions",
    ]
    if plugin_dir:
        command += ["--plugin-dir", str(plugin_dir)]
    try:
        env = {
            **os.environ,
            "CLAUDE_CONFIG_DIR": str(EVAL_CONFIG),
            "EVAL_PORT": str(free_port()),
            "AGENT_BROWSER_SESSION": pathlib.Path(cwd).name,
        }
        done = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        return {"is_error": True, "result": "", "error": f"timeout after {timeout}s"}
    try:
        return json.loads(done.stdout)
    except json.JSONDecodeError:
        return {"is_error": True, "result": done.stdout[-2000:], "error": done.stderr[-2000:]}


def judge(criteria, evidence):
    listed = "\n".join(f"- {name}: {text}" for name, text in criteria.items())
    prompt = (
        "You grade an evaluation. Judge each criterion against the evidence by meaning, not exact wording. "
        "The evidence is the agent's output unless it says otherwise. "
        'Answer with JSON only, one key per criterion: {"<name>": {"passed": true|false, "reason": "<one sentence>"}}.\n\n'
        f"Criteria:\n{listed}\n\nEvidence:\n{evidence}"
    )
    with tempfile.TemporaryDirectory() as folder:
        reply = claude(prompt, folder, JUDGE_MODEL, 2, 600)
    text = reply.get("result", "")
    match = re.search(r"\{.*\}", text, re.DOTALL)
    try:
        verdicts = json.loads(match.group(0)) if match else {}
    except json.JSONDecodeError:
        verdicts = {}
    results = {}
    for name in criteria:
        verdict = verdicts.get(name) if isinstance(verdicts.get(name), dict) else {}
        results[name] = {"passed": bool(verdict.get("passed")), "reason": verdict.get("reason", "no verdict: " + text[:120])}
    return results, reply.get("total_cost_usd", 0)


def tool_calls(transcript):
    calls = []
    if not transcript.exists():
        return calls
    for line in transcript.read_text(errors="replace").splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        message = record.get("message")
        if record.get("type") == "assistant" and isinstance(message, dict):
            for block in message.get("content") or []:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    calls.append({"name": block.get("name"), "input": block.get("input") or {}})
    return calls


class Run:
    def __init__(self, workdir, transcript, final):
        self.workdir = workdir
        self.transcript = transcript
        self.final = final
        self.calls = tool_calls(transcript)
        self.judge_cost = 0.0

    def judge(self, criteria, evidence):
        verdicts, cost = judge(criteria, evidence)
        self.judge_cost += cost
        return verdicts


def run_one(case_dir, case, arm_name, plugin_dir, index, out_root, model):
    out = out_root / case_dir.name / arm_name / str(index)
    out.mkdir(parents=True, exist_ok=True)
    workdir = pathlib.Path(tempfile.mkdtemp(prefix=f"mskills-eval-{case_dir.name}-{arm_name}-"))
    fixture = EVALS / case["fixture"] if "fixture" in case else case_dir / "fixture"
    if fixture.is_dir():
        shutil.copytree(fixture, workdir, dirs_exist_ok=True)
    setup = case_dir / "setup.py"
    if setup.exists():
        subprocess.run([sys.executable, "-I", str(setup)], cwd=workdir, check=True)
    subprocess.run(["git", "init", "-q"], cwd=workdir)
    subprocess.run(["git", "add", "-A"], cwd=workdir)
    subprocess.run(["git", "-c", "user.name=eval", "-c", "user.email=eval@example.com", "commit", "-q", "-m", "fixture"], cwd=workdir)
    started = datetime.datetime.now()
    reply = claude(case["prompt"], workdir, case.get("model", model), case.get("max_turns", 30), case.get("timeout", 900), plugin_dir)
    seconds = (datetime.datetime.now() - started).total_seconds()
    stop_leftovers(workdir, workdir.name)
    session_id = reply.get("session_id")
    transcript = transcript_path(workdir, session_id) if session_id else pathlib.Path("/nonexistent")
    final = reply.get("result", "") or ""
    (out / "final.md").write_text(final)
    if transcript.exists():
        shutil.copy(transcript, out / "transcript.jsonl")
    diff = subprocess.run(["git", "diff", "HEAD"], cwd=workdir, capture_output=True, text=True).stdout
    (out / "diff.patch").write_text(diff)
    run = Run(workdir, transcript, final)
    run.diff = diff
    grader = load_module(case_dir / "grade.py", f"grade_{case_dir.name}")
    grades = grader.grade(run)
    cost = {}
    if transcript.exists():
        measured = subprocess.run([sys.executable, "-I", str(SESSION_COST), str(transcript), "--json"], capture_output=True, text=True)
        cost = json.loads(measured.stdout).get("main", {}) if measured.returncode == 0 else {}
    weight = sum(item.get("weight", 1) for item in grades) or 1
    score = sum(item.get("weight", 1) for item in grades if item["passed"]) / weight
    result = {
        "case": case_dir.name,
        "arm": arm_name,
        "run": index,
        "score": round(score, 3),
        "grades": grades,
        "metrics": {key: value for item in grades for key, value in item.get("metrics", {}).items()},
        "usd": reply.get("total_cost_usd", 0),
        "judge_usd": round(run.judge_cost, 4),
        "turns": reply.get("num_turns"),
        "seconds": round(seconds),
        "error": reply.get("error") if reply.get("is_error") else None,
        "cost": cost,
        "workdir": str(workdir),
    }
    (out / "result.json").write_text(json.dumps(result, indent=2))
    return result


def regrade(folder):
    results = []
    for result_file in sorted(folder.glob("*/*/*/result.json")):
        out = result_file.parent
        result = json.loads(result_file.read_text())
        case_dir = EVALS / "cases" / result["case"]
        run = Run(pathlib.Path(result["workdir"]), out / "transcript.jsonl", (out / "final.md").read_text())
        run.diff = (out / "diff.patch").read_text()
        grades = load_module(case_dir / "grade.py", f"grade_{case_dir.name}").grade(run)
        weight = sum(item.get("weight", 1) for item in grades) or 1
        result["score"] = round(sum(item.get("weight", 1) for item in grades if item["passed"]) / weight, 3)
        result["grades"] = grades
        result["metrics"] = {key: value for item in grades for key, value in item.get("metrics", {}).items()}
        result["judge_usd"] = round(run.judge_cost, 4)
        result_file.write_text(json.dumps(result, indent=2))
        results.append(result)
    return results


def parse_arm(text):
    name, _, path = text.partition("=")
    return name, (pathlib.Path(path).resolve() if path else None)


def summarize(results):
    groups = {}
    for item in results:
        groups.setdefault((item["case"], item["arm"]), []).append(item)
    lines = ["| case | arm | runs | score | usd | turns | peak ctx | cache read | images | errors |", "|---|---|---|---|---|---|---|---|---|---|"]
    for (case, arm), items in sorted(groups.items()):
        count = len(items)

        def mean(values):
            values = [value for value in values if value is not None]
            return sum(values) / len(values) if values else 0

        lines.append(
            f"| {case} | {arm} | {count} | {mean(i['score'] for i in items):.2f} | "
            f"{mean(i['usd'] for i in items):.3f} | {mean(i['turns'] for i in items):.0f} | "
            f"{mean(i['cost'].get('peak_context') for i in items):,.0f} | "
            f"{mean(i['cost'].get('cache_read_input_tokens') for i in items):,.0f} | "
            f"{mean(i['cost'].get('images') for i in items):.1f} | "
            f"{sum(1 for i in items if i['error'])} |"
        )
    return "\n".join(lines)


def main():
    global EVAL_CONFIG
    EVAL_CONFIG = eval_config_dir()
    parser = argparse.ArgumentParser(description="Run mskills eval cases with and without the plugin.")
    parser.add_argument("--arm", action="append", help="NAME for no plugin, or NAME=PLUGIN_DIR")
    parser.add_argument("--regrade", type=pathlib.Path, help="grade an earlier results folder again")
    parser.add_argument("--case", action="append", help="case folder name; default all in the chosen set")
    parser.add_argument("--set", default="dev", choices=["dev", "holdout", "all"])
    parser.add_argument("--tier", action="append", help="S, M or L")
    parser.add_argument("--runs", type=int, help="override runs per case")
    parser.add_argument("--model", default="sonnet")
    parser.add_argument("-j", "--jobs", type=int, default=2)
    args = parser.parse_args()
    if args.regrade:
        results = regrade(args.regrade.resolve())
        summary = summarize(results)
        (args.regrade / "summary.md").write_text(summary + "\n")
        (args.regrade / "results.json").write_text(json.dumps(results, indent=2))
        print(summary)
        return
    if not args.arm:
        parser.error("--arm is required")
    cases = []
    for case_dir in sorted((EVALS / "cases").iterdir()):
        case_file = case_dir / "case.json"
        if not case_file.exists():
            continue
        case = json.loads(case_file.read_text())
        if args.case and case_dir.name not in args.case:
            continue
        if not args.case and args.set != "all" and case.get("set", "dev") != args.set:
            continue
        if args.tier and case.get("tier") not in args.tier:
            continue
        cases.append((case_dir, case))
    out_root = EVALS / "results" / datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    jobs = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        for case_dir, case in cases:
            for arm in args.arm:
                name, plugin_dir = parse_arm(arm)
                for index in range(args.runs or case.get("runs", 2)):
                    jobs.append(pool.submit(run_one, case_dir, case, name, plugin_dir, index, out_root, args.model))
        results = []
        for job in concurrent.futures.as_completed(jobs):
            result = job.result()
            results.append(result)
            print(f"{result['case']} {result['arm']}#{result['run']}: score {result['score']} usd {result['usd']:.3f} turns {result['turns']} error {result['error']}", flush=True)
    summary = summarize(results)
    (out_root / "summary.md").write_text(summary + "\n")
    (out_root / "results.json").write_text(json.dumps(results, indent=2))
    print(summary)
    print(f"results: {out_root}")


if __name__ == "__main__":
    main()
