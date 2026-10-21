---
name: ship-check
description: How to check a change properly before it ships, whether it's a UI, an app, a CLI, an API or a library. Use before saying work is done, before opening or merging a PR, before a release, and whenever asked to audit, inspect, QA, visually check or test what a change looks like and does. Covers what to check, in which order, how to collect before-and-after evidence, and how to report what was checked, fixed, left and never tried.
---

# Ship check

A check proves something only if it ran against the real thing, in the states a user
will meet, and the result was looked at. "Tests pass" is one layer of that, not the
whole of it.

## 1. Decide what has to be true

Before running anything, write down:

- **What changed** and every place a user meets it: screens, commands, endpoints,
  files it writes.
- **The rules it's checked against**: the project's agent instructions, design
  system, tokens, contracts and the task itself. Check against those, not your own
  taste. If a rule you need isn't written down, ask before fixing anything to it;
  fixing to a guessed rule gets redone.
- **The states that matter**: normal, empty, error, loading, very long content,
  the largest and smallest sizes the product supports, and whatever the change
  could break next to it. Drop a state the product can't reach (a size it never
  runs at, an orientation it's locked out of) and say so.

## 2. Check in layers, cheapest first

1. **Static**: typecheck, lint, formatter, the project's own quality checks.
2. **Tests**: the affected tests, then the suite the project runs before merging.
3. **Behaviour**: run the real program and use the changed path the way a user
   would. For a UI that means the running app, not a story or a unit render.
4. **Look**: only for what has to be seen. Read structure first (DOM, the
   accessibility tree, a layout dump, the response body) and look at a screenshot
   only for what structure can't tell you: text cut off, overlap, alignment.

Don't run a layer while a cheaper one is still failing.

## 3. Make the check trustworthy

- **Prove the harness first.** Run one state end to end and confirm it shows what
  you think it shows. A screenshot of the wrong screen, a test hitting a stale
  server or a request to the wrong port proves nothing.
- **Start clean.** Fixed data, a known account or fixture, no popups or leftover
  state from earlier runs. Put the environment back the way you found it after.
- **Same conditions before and after.** Capture the before state, fix, then capture
  the after state the same way, so the difference is the fix and nothing else.
- **Turn a rule into a test** when it can be checked by code (sizes, contrast,
  text scaling allowed, an error message shown), so it can't come back.

## 4. Fix

Fix what's in the task with the project's existing components, tokens and helpers.
Something you found outside the task gets reported, not fixed. Extra work someone
asks for midway is a separate piece: keep it in its own commit and say who asked.

## 5. Report

```
Checked: <layers run, states covered, where the evidence is>
Fixed:   <finding → fix → before/after evidence>
Left:    <real findings not fixed, and why>
Not tried: <what couldn't be checked here (real device, real account, a platform)>
```

Never call something working that wasn't run. "Not tried" is a normal answer, not a
failure to hide.

To run long checks without burning tokens, see the `cost-aware` skill.
