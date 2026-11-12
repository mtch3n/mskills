import ast
import collections
import io
import pathlib
import re
import subprocess
import tokenize

FIXTURE = pathlib.Path(__file__).parent / "fixture"
DIRECTIVE = re.compile(r"#\s*(noqa|type:\s*ignore|pragma|pyright:|mypy:|fmt:|isort:)")
REASON = re.compile(r"\bban|one hour|1 hour|\bhour\b", re.I)

HIDDEN_TESTS = '''
import json
import pytest
from orders.client import OrdersUnavailable, fetch_orders


def replies(*items):
    queue = list(items)
    return lambda path: queue.pop(0)


def ok():
    return (200, {}, json.dumps({"orders": [{"id": "A1"}]}))


def test_retries_then_succeeds():
    waits = []
    send = replies((429, {}, ""), (503, {}, ""), ok())
    assert fetch_orders(send, 7, sleep=waits.append) == [{"id": "A1"}]
    assert waits == [1, 2]


def test_gives_up_after_five_attempts():
    waits = []
    calls = []
    def send(path):
        calls.append(path)
        return (503, {}, "")
    with pytest.raises(OrdersUnavailable):
        fetch_orders(send, 7, sleep=waits.append)
    assert len(calls) == 5
    assert waits == [1, 2, 4, 8]


def test_retry_after_is_used_and_capped():
    waits = []
    send = replies((429, {"Retry-After": "12"}, ""), (429, {"Retry-After": "90"}, ""), ok())
    fetch_orders(send, 7, sleep=waits.append)
    assert [float(w) for w in waits] == [12, 30]


def test_other_errors_do_not_retry():
    waits = []
    with pytest.raises(OrdersUnavailable):
        fetch_orders(lambda path: (500, {}, ""), 7, sleep=waits.append)
    assert waits == []
'''


def comments(source):
    found = []
    try:
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            if token.type == tokenize.COMMENT and not token.string.startswith("#!") and not DIRECTIVE.match(token.string):
                found.append(token.string.strip())
    except (tokenize.TokenError, IndentationError, SyntaxError):
        pass
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return found
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            doc = ast.get_docstring(node, clean=False)
            if doc:
                found.append("docstring: " + doc.strip())
    return found


def python_files(root):
    return {str(p.relative_to(root)): p.read_text(errors="replace") for p in root.rglob("*.py") if ".venv" not in p.parts and "__pycache__" not in p.parts}


def grade(run):
    before = python_files(FIXTURE)
    after = python_files(run.workdir)
    added = []
    for name, source in after.items():
        extra = collections.Counter(comments(source)) - collections.Counter(comments(before.get(name, "")))
        added += [f"{name}: {text[:80]}" for text in extra.elements()]
    format_kept = after.get("orders/format.py") == before["orders/format.py"]
    stale_gone = "single attempt, there is no retry yet" not in after.get("orders/client.py", "")
    docs = [p for p in run.workdir.rglob("*.md") if ".venv" not in p.parts]
    changed_docs = [p for p in docs if p.read_text(errors="replace") != ((FIXTURE / p.relative_to(run.workdir)).read_text() if (FIXTURE / p.relative_to(run.workdir)).exists() else None)]
    reason_in_docs = any(REASON.search(p.read_text(errors="replace")) for p in changed_docs)
    hidden = run.workdir / "tests" / "test_hidden_retry.py"
    hidden.write_text(HIDDEN_TESTS)
    suite = subprocess.run(["uv", "run", "--quiet", "--with", "pytest", "python", "-m", "pytest", "-q", "-p", "no:cacheprovider"], cwd=run.workdir, capture_output=True, text=True, timeout=300)
    hidden.unlink()
    summary = (suite.stdout.strip().splitlines() or [""])[-1]
    return [
        {"name": "tests-pass", "passed": suite.returncode == 0, "weight": 2, "detail": summary},
        {"name": "no-added-comments", "passed": not added, "weight": 2, "detail": "; ".join(added[:6]), "metrics": {"added_comments": len(added)}},
        {"name": "stale-comment-removed", "passed": stale_gone, "weight": 1},
        {"name": "untouched-file-kept", "passed": format_kept, "weight": 1},
        {"name": "reason-in-docs", "passed": reason_in_docs, "weight": 1, "detail": ", ".join(str(p.relative_to(run.workdir)) for p in changed_docs)},
    ]
