---
name: no-comments
description: The code has no comments. Use when you write, edit or review code, tests, styles, config, CI workflows or scripts, and before you commit, to keep comments out and to move the reason for the code into the docs.
---

# No comments

**Do not add a comment.** This applies to every comment syntax in every file,
including docstrings, JSDoc, HTML and CSS comments, `#` lines in config and CI
workflows, and commented-out code.

## Where the words go

- **What the code does** goes in names: a named function, constant, type or test.
- **Why the code is so** (a limit, a risk, a vendor rule, a decision) goes in the
  project's docs: the README, `docs/` or an ADR. If an agent that edits the code
  must know it, put it in `CLAUDE.md` or `AGENTS.md`. Write it there in the same
  change. Do not drop it.
- **History** goes in the commit message. **TODOs** go in the issue tracker.

## Allowed

- Tool directives with no prose, such as `# noqa`, `# type: ignore`,
  `eslint-disable-next-line`, `@ts-expect-error`, `# shellcheck` and `//go:build`.
- Shebangs, and encoding or mode lines that a tool reads.
- Generated and vendored files. Do not edit their comments.
- Strings are not comments: `#` in a here-document, a template, Markdown or a regex.

## Existing comments

When you change a line or a block that has a comment, delete the comment. If it
gives a reason that is not in the docs, move the reason to the docs first. Do not
remove comments from files that you do not change.

## Before you commit

Check the lines that you added:

```bash
git diff HEAD -U0 | grep -E '^\+(#|.*(\s#|//|/\*|\*/|<!--|"""|'"'''"'))'
```

Each hit is an allowed line, a string or a comment to remove. If the project has a
comment checker or a lint rule for this, run it instead.

To clean all comments out of a diff or a set of files, use the `comment-reviewer`
agent (`mskills:comment-reviewer`).
