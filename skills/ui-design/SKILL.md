---
name: ui-design
description: How to design or redesign a UI screen without AI slop and without long correction loops. Use before you design, redesign, restyle or "make it look professional" any screen, before you show design options or mockups, and when the user rejects a design ("I don't like it", "still bad", "looks like a toy", "AI slop").
---

# UI design

In the user's history, the longest UI loops were design loops, not pixel loops. The
agent invented a look with no reference. It showed "options" that were one layout in
three colours. It forgot a rule from an earlier message. It added text, tabs and
decoration that nobody asked for. Each step below stops one of these causes.

Use the `ui-antislop` skill to measure the result. This skill is about what to build.
In the commands, `<ui-antislop>` is the `ui-antislop` folder next to this skill's folder.

## 1. Before you design

1. Read the rules: `DESIGN.md`, the UI section of `CLAUDE.md` or `AGENTS.md`, and the
   user's last messages about this screen. Write a short checklist of the rules that
   apply, for example "shadcn default theme, no brand colour in components, no card
   inside a card".
2. Get one reference. If the user says "redesign", "more professional" or "premium"
   and gives no reference, ask for one product that the screen must feel like, and
   ask what to keep. Do not guess a style.
3. Write in one line what the screen shows: the navigation model, the groups and the
   one primary action. If a word in the request can mean two things, ask. For
   example, "app catalog" can mean a list of items or a grid of plugins.
4. Use the terms of the platform and of the product. Do not invent a label. Use the
   words that common settings pages and the reference product use.

## 2. Options

1. If you show options, make each option different in structure: navigation,
   density, groups or the order of the content. A new colour scheme is not a new
   option.
2. Measure the options with
   `uv run --script <ui-antislop>/scripts/ui-antislop.py <option pages> --variants`.
   If two options share one layout, replace one of them.
3. Show at most 3 options. Give each option one line that tells how it is different.
4. Open the options where the user can see them, and say where they are. Do not make
   the user ask for the file.
5. If the user rejects all options two times, do not make more options. Ask the user to
   describe or sketch the structure, and build that.

## 3. Add nothing that the user did not ask for

Do not add these items if the user or the rules do not ask for them:

- Helper sentences, hints, "demo data" banners and success text that stays.
- Tabs, pages, screens or settings that have no task.
- Status decoration: dots that pulse, progress rings, "updated just now", spinners on
  static data, badges.
- Boxes: a card around one item, a card inside a card, a tinted box, a stripe on one
  side, a container with a shadow.
- Separators between items that space already separates.

If you think that the screen needs one of these items, ask.

## 4. Words

1. Read each sentence on the screen. If it does not help the next action or prevent a
   mistake, remove it. Do not write it again in other words.
2. Name a control with its action, for example "Save". Do not write "Click here to
   save your changes".
3. In an error, tell the problem and how to fix it.
4. Do not explain on the screen how the system works inside. Put that in the docs.

## 5. Build

1. Use the project's components and tokens. Run
   `python3 <ui-antislop>/scripts/slop-lint.py` after each edit. It reads the lines
   that you added and reports raw colours, arbitrary sizes and slop patterns.
2. When you change a size, give the old value, the new value and the source of the
   new value: a token, the reference or the user.
3. If the user approved a mockup, compare the built screen with the mockup before you
   report. Check that each approved part is there and is in the same place.
4. For a new screen or a redesign, after `ui-antislop` has no `F` line, start the
   `ui-reviewer` agent. Give it the pages, the user's request and the path to the
   `ui-antislop` skill. Fix each problem that it returns, or tell the user why you keep
   it. Do not start it for a small fix.

## 6. When the user rejects the result

1. Write the correction in the rules file in the user's words.
2. Re-read your checklist from step 1. If the last change broke a rule, say so.
3. Fix the cause on every screen, not only on the screen in the screenshot.
4. Answer with the fix and a screenshot. Do not answer a UI complaint with a test
   report or a question about the process.

## Default rules

`<ui-antislop>/references/slop.md` has the user's default rules. The project's rules win.
