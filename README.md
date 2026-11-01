# mskills

MTChen's personal agent skills, for every project. Plain
[Agent Skills](https://agentskills.io) (`skills/<name>/SKILL.md`) plus a Claude Code
plugin that ships them with a hook.

## Skills

| Skill | What it does |
|---|---|
| [`worktrees`](skills/worktrees/SKILL.md) | Git worktrees live at `<main-repo>/.claude/worktrees/<name>`. How to create, move and remove them, and how to git-ignore `.claude/worktrees/`. |
| [`recall`](skills/recall/SKILL.md) | Finds every past session about one task, pulls that task out, fact-checks it against the real files, git and tools, and writes a focused brief plus a handoff prompt for a fresh session. Run it with `/mskills:recall <task>`. |
| [`no-comments`](skills/no-comments/SKILL.md) | The code has no comments. Names carry the *what*, the docs carry the *why*; only tool directives are allowed. |
| [`ship-check`](skills/ship-check/SKILL.md) | How to check a change before it ships: what has to be true, layers from static checks to a real look, trustworthy before-and-after evidence, and a report of what was checked, fixed, left and never tried. |
| [`ste100`](skills/ste100/SKILL.md) | Writes English in ASD-STE100 Simplified Technical English and rewrites dense or ambiguous English into it, with a checker for the measurable rules. |
| [`cost-aware`](skills/cost-aware/SKILL.md) | How an agent keeps token cost down: big things stay out of the main context, fewer turns, less work, and the right worker for each job. |
| [`ui-check`](skills/ui-check/SKILL.md) | Measures a rendered web page for alignment, gaps, overflow, clipped text, contrast, focus and AI-slop patterns. It also lints UI source for raw colours and slop. Default UI rules are in [`references/slop.md`](skills/ui-check/references/slop.md). Needs `uv`. |
| [`ui-design`](skills/ui-design/SKILL.md) | How to design or redesign a screen without long correction loops. Get a reference, make options that differ in structure, and add nothing that nobody asked for. |

## Agents

| Agent | Model | What it does |
|---|---|---|
| [`comment-reviewer`](agents/comment-reviewer.md) | inherits | Applies `no-comments` to a diff or files: removes the comments, writes their reasons into the docs, suggests renames. |
| [`session-reader`](agents/session-reader.md) | Sonnet | Reads past sessions for `recall` and returns one task's claims, marked as said by the user or the agent. |
| [`ui-reviewer`](agents/ui-reviewer.md) | Sonnet | Reviews a rendered screen for what measurement cannot find: hierarchy, the primary action, words that do not help, structure and the project's rules. Does not change files. |

## Hooks

| Hook | Event | What it does |
|---|---|---|
| [`worktree-guard.py`](hooks/worktree-guard.py) | `PreToolUse` on `Bash` | Denies `git worktree add` and `git worktree move` to any path other than `<main-repo>/.claude/worktrees/<name>`. How it works: [`docs/worktree-guard.md`](docs/worktree-guard.md). Needs `git`. |
| [`ui-correction.py`](hooks/ui-correction.py) | `UserPromptSubmit` | When the user's message corrects a UI, tells the agent to write the rule in the rules file and to measure before and after. |
| [`ui-lint.py`](hooks/ui-lint.py) | `PostToolUse` on edits | Runs `slop-lint` on the lines that the agent just wrote to a UI file and gives it the findings. |
| [`ui-stop.py`](hooks/ui-stop.py) | `Stop` | When the agent changed UI files, finds the pages that use them and measures them with `ui-check --stress --interact`. Gives the agent the problems to fix, up to 3 times while a fail stays. |

All hooks need `python3`.

## Install

Claude Code:

```bash
claude plugin marketplace add mtch3n/mskills
claude plugin install mskills@mskills
```

Then run `/reload-plugins` in an open session, or start a new one. Skills appear as
`/mskills:worktrees`, `/mskills:no-comments`, `/mskills:recall`, `/mskills:ship-check`,
`/mskills:cost-aware`, `/mskills:ste100`, `/mskills:ui-check` and `/mskills:ui-design`. The hooks start
automatically.

Other agents (skills only, no hooks):

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
