# mskills

MTChen's personal agent skills, for every project. Plain
[Agent Skills](https://agentskills.io) (`skills/<name>/SKILL.md`) plus a Claude Code
plugin that ships them with a hook.

## Skills

| Skill | What it does |
|---|---|
| [`worktrees`](skills/worktrees/SKILL.md) | Git worktrees live at `<main-repo>/.claude/worktrees/<name>`. How to create, move and remove them, and how to git-ignore `.claude/worktrees/`. |
| [`no-comments`](skills/no-comments/SKILL.md) | The code has no comments. Names carry the *what*, the docs carry the *why*; only tool directives are allowed. |

## Agent

[`comment-reviewer`](agents/comment-reviewer.md) applies `no-comments` to a diff or
files: removes the comments, writes their reasons into the docs, and suggests the
renames that make the code read without them.

## Hook

[`hooks/worktree-guard.py`](hooks/worktree-guard.py) is a `PreToolUse` hook on `Bash`
that denies `git worktree add` and `git worktree move` to any path other than
`<main-repo>/.claude/worktrees/<name>`. How it works:
[`docs/worktree-guard.md`](docs/worktree-guard.md). Needs `python3` and `git`.

## Install

Claude Code:

```bash
claude plugin marketplace add mtch3n/mskills
claude plugin install mskills@mskills
```

Then run `/reload-plugins` in an open session, or start a new one. Skills appear as
`/mskills:worktrees` and `/mskills:no-comments`; the hook runs on every Bash call.

Other agents (skills only, no hook):

```bash
npx skills add mtch3n/mskills
```

### One-time setup: ignore `.claude/worktrees/` globally

Without it, every repo shows `.claude/` as untracked and `git add -A` commits a
worktree as an embedded repository.

```bash
mkdir -p ~/.config/git
grep -qxF '.claude/worktrees/' ~/.config/git/ignore 2>/dev/null \
  || echo '.claude/worktrees/' >> ~/.config/git/ignore
```

If `git config --global core.excludesFile` prints a path, add the line there instead.

## Layout

```
.claude-plugin/   Claude Code plugin and marketplace manifests
.cursor-plugin/   Cursor plugin manifest
plugin.json       agent-plugins.org manifest
skills/           one folder per skill
agents/           subagents the skills hand work to
hooks/            Claude Code hooks (hooks.json + scripts)
docs/             the why behind the hooks and skills
```

## License

MIT
