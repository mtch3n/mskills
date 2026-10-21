#!/usr/bin/env python3
import json
import os
import re
import shlex
import subprocess
import sys

WRAPPERS = {"sudo", "doas", "env", "command", "nohup", "time", "exec"}
ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
GIT_OPTS_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}
ADD_OPTS_WITH_VALUE = {"-b", "-B", "--reason"}
UNRESOLVED = re.compile(r"[$`*?\[]")


class Unresolvable(Exception):
    pass


def is_operator(tok):
    return bool(tok) and all(c in "();<>|&\n" for c in tok)


def unquote(tok):
    if len(tok) >= 2 and tok[0] in "\"'" and tok[-1] == tok[0]:
        return tok[1:-1]
    return tok


def simple_commands(command):
    lexer = shlex.shlex(command, posix=False, punctuation_chars=True)
    lexer.whitespace_split = True
    out, cur = [], []
    for tok in lexer:
        if is_operator(tok):
            if cur:
                out.append(cur)
                cur = []
        else:
            cur.append(tok)
    if cur:
        out.append(cur)
    return out


def strip_prefix(cmd):
    i = 0
    while i < len(cmd):
        if ASSIGNMENT.match(cmd[i]):
            i += 1
        elif unquote(cmd[i]) in WRAPPERS:
            i += 1
            while i < len(cmd) and cmd[i].startswith("-"):
                i += 1
        else:
            break
    return [unquote(t) for t in cmd[i:]]


def resolve(base, path):
    path = os.path.expandvars(os.path.expanduser(path))
    if UNRESOLVED.search(path):
        raise Unresolvable(path)
    return os.path.normpath(os.path.join(base, path))


def positionals(args, opts_with_value):
    out, i = [], 0
    while i < len(args):
        a = args[i]
        if a == "--":
            out.extend(args[i + 1:])
            break
        if a in opts_with_value:
            i += 2
            continue
        if not a.startswith("-"):
            out.append(a)
        i += 1
    return out


def worktree_target(argv, cwd):
    i = 1
    git_dir = cwd
    while i < len(argv) and argv[i].startswith("-"):
        opt = argv[i]
        if opt == "-C" and i + 1 < len(argv):
            git_dir = resolve(git_dir, argv[i + 1])
        if opt in GIT_OPTS_WITH_VALUE:
            i += 2
        else:
            i += 1
    if argv[i:i + 1] != ["worktree"] or i + 1 >= len(argv):
        return None
    action, rest = argv[i + 1], argv[i + 2:]
    if action == "add":
        pos = positionals(rest, ADD_OPTS_WITH_VALUE)
        return (git_dir, resolve(git_dir, pos[0])) if pos else None
    if action == "move":
        pos = positionals(rest, set())
        return (git_dir, resolve(git_dir, pos[1])) if len(pos) >= 2 else None
    return None


def main_repo(git_dir):
    out = subprocess.run(
        ["git", "-C", git_dir, "rev-parse", "--path-format=absolute", "--git-common-dir"],
        capture_output=True, text=True, timeout=5,
    )
    if out.returncode != 0:
        raise Unresolvable(git_dir)
    common = out.stdout.strip()
    if os.path.basename(common) != ".git":
        raise Unresolvable(common)
    return os.path.dirname(common)


def check(command, cwd):
    denials = []
    for cmd in simple_commands(command):
        argv = strip_prefix(cmd)
        if not argv:
            continue
        if argv[0] == "cd" and len(argv) >= 2:
            cwd = resolve(cwd, argv[1])
            continue
        if argv[0] != "git":
            continue
        found = worktree_target(argv, cwd)
        if not found:
            continue
        git_dir, target = found
        root = main_repo(git_dir)
        allowed = os.path.join(root, ".claude", "worktrees")
        if os.path.dirname(target) != allowed:
            name = os.path.basename(target.rstrip("/")) or "<name>"
            denials.append(
                "Worktrees go in the main repo's `.claude/worktrees/<name>` "
                f"(git-ignored globally), not `{target}`. Use: "
                f"`git -C {root} worktree {argv[argv.index('worktree') + 1]} "
                f"... {allowed}/{name}`."
            )
    return denials


def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if payload.get("tool_name") != "Bash":
        return 0
    command = (payload.get("tool_input") or {}).get("command")
    if not isinstance(command, str) or "worktree" not in command:
        return 0
    cwd = payload.get("cwd") or os.getcwd()

    try:
        denials = check(command, cwd)
    except (ValueError, Unresolvable, OSError, subprocess.SubprocessError):
        return 0

    if denials:
        json.dump(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": " ".join(dict.fromkeys(denials)),
                }
            },
            sys.stdout,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
