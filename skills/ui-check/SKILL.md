---
name: ui-check
description: Measures a rendered web page for misaligned edges, uneven gaps, overflow, overlap, cut-off text, low contrast, small targets and AI-slop patterns, lints UI source for raw colours and slop, and draws a frame over a screenshot. Use when you build, change or review a web UI, before you say a UI change is done, and when the user says a UI looks wrong, "doesn't line up", "looks bad" or "AI slop".
---

# UI check

An agent that looks at a screenshot does not see a 2 px step, a clipped button or a
chip that is 1 px smaller. Measure the rendered page, and let the numbers decide.
The scripts are in this skill's base directory. They need `uv`.

## 1. Before you build

1. Read the project's design rules: `DESIGN.md`, or the UI section of `CLAUDE.md` or
   `AGENTS.md`. If there are no rules, make `DESIGN.md`. Read `references/slop.md`
   for the default rules. The project's rules win.
2. Use the project's components and tokens. Do not write a raw color.
3. For a new screen or a redesign, use the `ui-design` skill.

## 2. Measure

```bash
uv run --script <base>/scripts/ui-check.py <page> [<page> ...] --stress --interact
```

- A page is a URL or a local HTML file. Give every page that uses the part you
  changed.
- Run it one time before you change the code, to find every problem on the page,
  and one time when you think that you are done.
- In Claude Code, a hook measures the pages again when you stop. Fix what it reports.
- `python3 <base>/scripts/slop-lint.py [<file> ...]` checks the source for raw colors
  and slop. With no file, it checks the lines that you added. In a shadcn project, it
  also reports each native element that has a shadcn component.
- If the browser is not installed, run
  `uvx playwright@1.63.0 install chromium-headless-shell` one time.

The kinds, the options and the hooks are in `references/kinds.md`.

## 3. Read the result

- `F`: a defect. Fix it. Do not report the work as done while an `F` stays.
- `W`: fix it, or tell the user why the project's rules allow it.
- `S`: a slop pattern. Remove it if no rule asks for it.
- A finding for words (`helper-text`, `restates`, `filler`, `chatty`): remove the
  text. Do not write it again in other words.
- Fix the cause in the shared style when the same problem is on several pages.
- Do not remove content to make a check pass.

## 4. When the user complains

1. Write the complaint as a rule in the rules file. Use the user's words.
2. Find every instance of the problem on every page, not only the one that the user
   named.
3. Change only what the user named. Measure with `--out <dir>/before` first, and with
   `--baseline <dir>/before` after. Undo each change that is not part of the task.

## 5. Report

Tell the pages and widths that you measured, the number of fails, warns and smells
before and after, and each warn or smell that you kept with the reason.
