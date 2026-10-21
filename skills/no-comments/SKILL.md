---
name: no-comments
description: The code has no comments. Use whenever writing, editing or reviewing code, tests, styles, config, CI workflows or shell scripts, and before committing, to keep comments out, to decide whether a line is an allowed tool directive, and to move a comment's reason into the project's docs.
---

# No comments

**The code has no comments. Do not add any.** Comments go stale, and agents trust them
over the code.

That covers every comment syntax in every file you write: `//`, `/* */`, JSDoc and
other doc comments (`/** */`, `///`, `//!`, Python docstrings), `{/* */}` in JSX, CSS
and SCSS, `<!-- -->` in HTML and XML templates, tests, and `#` lines in Python, shell,
YAML (CI workflows and actions), TOML, Dockerfiles, Makefiles and other config.
Commented-out code too: delete it, git has it.

## Where the words go instead

- **The *what*** goes in names. Extract a well-named function, constant, type or test
  instead of explaining a block. A magic value becomes a named constant; a tricky
  condition becomes a named predicate.
- **The *why*** goes in the project's docs, not the code: the design doc, `docs/`,
  an ADR, or the README. If an agent editing that code must know it, put it in the
  project's agent instructions (`CLAUDE.md`, `AGENTS.md`). A reason for a CI job
  goes in the docs too, by workflow file and job name, never in the workflow.
- **The history** (what changed, which bug it fixed) goes in the commit message.
- **TODOs** go in the issue tracker.

## Allowed

Only lines a tool reads, plus the lines a file needs to run:

- Tool directives: `biome-ignore`, `eslint-disable-next-line`, `@ts-expect-error`,
  `/// <reference>`, `# shellcheck`, `# yaml-language-server`, `# noqa`,
  `# type: ignore`, `//go:build`, `//go:generate`, `// prettier-ignore` and the like.
  A directive carries no prose beyond what the tool requires as its reason.
- Shebangs (`#!/usr/bin/env python3`) and encoding or mode lines a tool parses.

Exempt: generated and vendored files (codegen output, lockfiles, copied-in UI kits
such as shadcn components). Hand edits to them don't need their comments removed.

Not comments: strings. `#` lines inside a here-document, a template string, a
generated shell rc, a Markdown heading, or a regex stay.

## Existing comments

Never add one. When you change a line that carries a comment, delete the comment;
if it held a real *why* that isn't written down, move it to the docs first. Don't
sweep untouched files unless asked.

## Before you commit

Check the lines you added, not the whole repo:

```bash
git diff --cached -U0 | grep -E '^\+(#|.*(\s#|//|/\*|\*/|<!--|"""|'"'''"'))'
```

Every hit is either an allowed directive, a string, or a comment to remove. Rename or
extract until the code reads without it, and move any *why* to the docs.

If the project already has a comment checker or a lint rule for this, run that
instead and leave the grep.

## Sweeping a change

For a whole diff or a set of files, use the `comment-reviewer` agent
(`mskills:comment-reviewer` in Claude Code) and give it the scope. It removes the
comments and writes their reasons into the docs; you make the renames it suggests.
