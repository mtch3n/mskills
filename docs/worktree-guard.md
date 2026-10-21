# worktree-guard

`hooks/worktree-guard.py` is a Claude Code `PreToolUse` hook on `Bash`. It denies any
`git worktree add` or `git worktree move` whose target is not
`<main-repo>/.claude/worktrees/<name>`.

## Why

`.claude/worktrees/` is git-ignored globally, so a worktree there is invisible to the
main repo. A sibling folder (`../repo-feat`) scatters checkouts across the disk where
nobody finds them again.

## How it decides

- Checks `git worktree add <path>` and `git worktree move <wt> <new-path>`.
- Resolves the target path against the payload's `cwd`, any earlier `cd` in the same
  command, and `git -C`.
- Finds the main repo with `git rev-parse --git-common-dir`, so running the command
  from inside another worktree still maps to the main checkout.
- Skips leading `VAR=value` assignments and wrappers (`sudo`, `env`, `command`, `nohup`,
  `time`, `exec`, `doas`).
- Fails open: anything unparseable or unresolvable (globs, `$VAR` it can't expand,
  bare repos, a directory that isn't a repo) is allowed through.

## Contract

[Claude Code hooks](https://code.claude.com/docs/en/hooks):

- stdin: `{"tool_name": "Bash", "tool_input": {"command": ...}, "cwd": ...}`
- stdout: `hookSpecificOutput.permissionDecision: "deny"` with a reason naming the
  allowed path blocks the call. Empty stdout allows it.

Needs `python3` and `git` on `PATH`.
