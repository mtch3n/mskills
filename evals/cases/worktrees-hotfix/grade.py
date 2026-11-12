import pathlib
import subprocess


def git(app, *args):
    return subprocess.run(["git", "-C", str(app), *args], capture_output=True, text=True).stdout


def worktrees(app):
    found = []
    entry = {}
    for line in git(app, "worktree", "list", "--porcelain").splitlines() + [""]:
        if not line:
            if entry:
                found.append(entry)
            entry = {}
            continue
        key, _, value = line.partition(" ")
        entry[key] = value
    return found


def grade(run):
    app = (run.workdir / "app").resolve()
    branch = [w for w in worktrees(app) if w.get("branch") == "refs/heads/fix/tax-rounding"]
    path = pathlib.Path(branch[0]["worktree"]).resolve() if branch else None
    expected = app / ".claude" / "worktrees" / "fix-tax-rounding"
    in_folder = bool(path) and path.parent == app / ".claude" / "worktrees"
    status = git(app, "status", "--porcelain", "--untracked-files=all")
    head = git(app, "rev-parse", "--abbrev-ref", "HEAD").strip()
    main_kept = (
        head == "main"
        and " M README.md" in status
        and "?? report.py" in status
        and "tax.py" not in status
        and git(app, "log", "--format=%s", "main").split() == ["tax"]
    )
    fix_files = git(app, "diff", "--name-only", "main", "fix/tax-rounding").split()
    fixed = False
    detail = ""
    if path and path.is_dir():
        check = subprocess.run(["python3", "-I", "-c", "import sys; sys.path.insert(0, '.'); from tax import tax; print(tax(2.675, 1), tax(100, 0.2), tax(1.005, 1))"], cwd=path, capture_output=True, text=True)
        detail = check.stdout.strip() or check.stderr.strip()[-200:]
        fixed = detail.split()[:3] == ["2.68", "20.0", "1.01"] or detail.split()[:3] == ["2.68", "20.00", "1.01"]
    committed = "tax.py" in fix_files and any(name.startswith("test") or "/test" in name for name in fix_files)
    return [
        {"name": "worktree-in-claude-folder", "passed": in_folder, "weight": 2, "detail": str(path)},
        {"name": "worktree-named-after-branch", "passed": path == expected, "weight": 1, "detail": str(path)},
        {"name": "main-checkout-kept", "passed": main_kept, "weight": 2, "detail": f"head={head} status={status.strip()!r}"},
        {"name": "fix-committed-on-branch", "passed": committed, "weight": 1, "detail": " ".join(fix_files)},
        {"name": "fix-correct", "passed": fixed, "weight": 1, "detail": detail},
    ]
