---
name: worktrees
description: Where git worktrees live and how to create, move and remove them. Use before running `git worktree add`, `git worktree move` or `git worktree remove`, when starting work on a branch in parallel with the main checkout, or when a worktree command was denied by the worktree guard.
---

# Worktrees

Every git worktree lives at `<main-repo>/.claude/worktrees/<name>`. Never a sibling
folder (`../repo-feat`), never `/tmp`, never anywhere else.

`<main-repo>` is the main checkout, not another worktree. From anywhere inside the repo:

```bash
git rev-parse --path-format=absolute --git-common-dir
```

prints `<main-repo>/.git`; its parent is `<main-repo>`.

## Commands

Use `git -C <main-repo>` so the relative path resolves against the main checkout no
matter where you run it.

```bash
git -C /home/u/proj worktree add .claude/worktrees/feat-x -b feat/x
git -C /home/u/proj worktree add .claude/worktrees/fix-y fix/y
git -C /home/u/proj worktree move .claude/worktrees/feat-x .claude/worktrees/feat-x2
git -C /home/u/proj worktree remove .claude/worktrees/feat-x
git -C /home/u/proj worktree prune
git -C /home/u/proj worktree list
```

- Name the folder after the branch, with `/` replaced by `-`.
- Remove the worktree when its branch is merged or abandoned. `remove` refuses a dirty
  worktree; commit, stash or discard first. Use `--force` only for work you have
  confirmed is disposable.

## The guard

mskills ships a `PreToolUse` hook that denies `git worktree add` and `git worktree move`
when the target isn't `<main-repo>/.claude/worktrees/<name>`. If it denies a command,
rerun it with the path the denial message names. Don't route around it with another
tool or a script. Details: `docs/worktree-guard.md` in the mskills repo.

## `.claude/worktrees/` must be git-ignored

Without the ignore, the main repo shows `.claude/` as untracked, and `git add -A`
commits the worktree as an embedded repository (a gitlink).

Ignore it once for every repo with git's global excludes file
(`core.excludesFile`, default `~/.config/git/ignore`):

```bash
mkdir -p ~/.config/git
grep -qxF '.claude/worktrees/' ~/.config/git/ignore 2>/dev/null \
  || echo '.claude/worktrees/' >> ~/.config/git/ignore
```

If `git config --global core.excludesFile` prints a path, add the line to that file
instead. Check it from any repo with a worktree:

```bash
git -C /home/u/proj check-ignore -v .claude/worktrees/feat-x
```

It must print the matching ignore rule. Don't add the line to a project's own
`.gitignore` unless that project wants it there; the global ignore covers it.
