---
name: ui-design
description: How to design or redesign a UI screen without AI slop and without long correction loops. Use before you design, redesign, restyle or "make it look professional" any screen, before you show design options or mockups, and when the user rejects a design ("I don't like it", "still bad", "looks like a toy", "AI slop").
---

# UI design

In the user's history, the longest UI loops were design loops, not pixel loops. The
agent invented a look with no reference. It showed "options" that were one layout in
three colours. It forgot a rule from an earlier message. Each step below stops one of
these causes.

Use the `ui-antislop` skill to measure the result. This skill is about what to build.
In the commands, `<ui-antislop>` is the `ui-antislop` folder next to this skill's folder.

## 1. Before you design

1. Read the user's last messages about this screen. Write a short checklist of what
   the user asked for.
2. Get one reference. If the user says "redesign", "more professional" or "premium"
   and gives no reference, ask for one product that the screen must feel like, and
   ask what to keep. Do not guess a style.
3. Write in one line what the screen shows: the navigation model, the groups and the
   one primary action. If a word in the request can mean two things, ask. For
   example, "app catalog" can mean a list of items or a grid of plugins.

## 2. Options

1. Show at most 3 options. Give each option one line that tells how it is different.
2. Open the options where the user can see them, and say where they are. Do not make
   the user ask for the file.
3. If the user rejects all options two times, do not make more options. Ask the user to
   describe or sketch the structure, and build that.

## 3. Build

1. When you change a size, give the old value, the new value and the source of the
   new value: a token, the reference or the user.
2. If the user approved a mockup, compare the built screen with the mockup before you
   report. Check that each approved part is there and is in the same place.
3. For a new screen or a redesign, after `ui-antislop` has no `F` line, start the
   `ui-reviewer` agent. Give it the pages, the user's request and the path to the
   `ui-antislop` skill. Fix each problem that it returns, or tell the user why you keep
   it. Do not start it for a small fix.

## 4. When the user rejects the result

1. Re-read your checklist from step 1. If the last change broke an item of it, say so.
2. Answer with the fix and a screenshot. Do not answer a UI complaint with a test
   report or a question about the process.

## Default rules

`<ui-antislop>/references/slop.md` has the user's default rules. The project's rules win.
