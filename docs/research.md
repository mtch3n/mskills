# Research and decisions, October 2026

This file records the research, the design decisions and the eval baseline for the
next version of the mskills skills. The work is paused. The last section gives the
next steps.

## Why this work started

A Sonnet worker did a UI audit of a mobile app (session `7f8637bc`, 2026-10-19). It
found and fixed real problems, but the cost was high:

- 216 turns. The context grew from 30k to 337k tokens.
- 38.7M cache-read tokens, about 80% of the cost. Each turn reads the full context
  again.
- 32 images went into the main context and stayed there.
- The "before" sweep ran 3 times. A notification blocked taps, the app was paired to
  a gateway that did not exist, and the navigation took screenshots of wrong screens.
- 51 wait calls. The worker swept landscape, but the app has a portrait lock.
- A coordinator added 10 review items in the middle of the run.
- A later PR changed the 48dp button sizes to compact sizes. The work was done two
  times.

## What other skill collections do

Sources: pstack (`backnotprop/pstack`) and the Cursor plugins (`cursor/plugins`). We
use their ideas and structure only. We do not copy their text.

- **Small principle skills.** Each one holds one rule in a few lines.
- **Playbooks.** Each one starts with "You own X", gives numbered steps, gives rules
  against shortcuts, and ends with a fixed reply format.
- **Verification in two layers.** A generic method, plus a harness that is specific to
  the project (launch, doctor, drive, evidence, cleanup, helpers). pstack generates
  the harness with `create-verification-skill`.
- **Claims and verdicts.** Cursor `verify-this` writes a claim that a test can prove
  false. It compares a baseline with a treatment under the same conditions. The
  verdict is one of VERIFIED, NOT VERIFIED or INCONCLUSIVE.
- **Skill writing.** Delete text that does not change a decision. Refer to other
  skills by path. Do not repeat them.

## Design agreed with Codex

Two review rounds with Codex (the second used `gpt-6-astra` at `xhigh`) ended with
no disagreements.

1. **Three layers.** Short principle skills, generic method skills, and a harness that
   each project owns. Do not add a router skill until triggers collide.
2. **`knowledge-kinds`** (new principle skill). It names six kinds of knowledge:
   `harness-recipe`, `rules-constraints`, `finding-lesson`, `evidence-artifact`,
   `cost-baseline`, `handoff-state`. Each item records its kind, content, source,
   scope and verification state. To choose where an item goes:
   1. Use the knowledge tool that the session has (for example Trellis), with its
      own rules.
   2. If there is no tool, use the place that the project already uses.
   3. If there is no such place, ask the user one time for each project in the run.
   4. If there is no answer, put the item in the reply.
   Never start a new store. mskills does not depend on Trellis and has no adapter
   for it.
3. **`ship-check`** (rewrite). Sections: Claims, Environment, Pilot, Verification,
   Cleanup, Reply. Each claim has an ID and an acceptance criterion. Lock the scope
   and put new requests in a queue. Record the environment. Prove one full path
   before you expand. Limit retries. Keep harness failures separate from product
   failures. Verdicts: PASS, FAIL, INCONCLUSIVE, NOT RUN. Reply table:
   `ID | criterion | status | evidence | limitation/next action`.
4. **`cost-aware`** (make it shorter). Sections: Working rules, Measure, Reply.
   `scripts/session-cost.py` reports turns, peak context, token totals, images and
   wait calls. Thresholds give warnings only. The script exists now and has tests.
5. **Tests** go next to each script in `scripts/tests/`. Use the standard library
   only.
6. **Phase 2.** `make-verify` makes and proves a project harness and keeps its recipe
   as a `harness-recipe`. A Sonnet `screen-checker` agent reads screenshots and
   returns text only.
7. **Size.** Keep each skill small. Keep descriptions to 25-35 words, because every
   session loads every description.

Open decision: `no-comments` sends the *why* to the docs or `CLAUDE.md`. That
conflicts with "never start a new store". The proposal is to keep those places as
defaults and add "or the knowledge tool of the session".

## ASD-STE100 research

Sources: the Issue 9 text (January 2025), community skills (danyuchn, nuelcyoung,
starise, toppa, Hermes, PostHog), Vale STE styles and spaCy linters.

- The `ste100` skill and checker now follow Issue 9 (commit `bc0d401`). The verb
  forms, the passive rule, the approved *-ing* words, modal verbs, contractions,
  word counts and the limits for notes and warnings are correct.
- The official dictionary and specification are copyrighted. Only listed groups can
  reproduce them. ASD-STE100 is an EU trademark. We ship no dictionary, we use our
  own words, and we say that the skill is unofficial.
- Do not copy the word lists from `0xpili/simplified-technical-english`, the
  dictionary file from `nuelcyoung`, or the PDF in `sourdough-bread/asd-ste100-checker`.
- Possible later additions: a word replacement list that we write, a Vale style, an
  output style that is always on, and an optional spaCy mode.

The checker ran on 2,516 recent agent replies (550k words). It found 3,455
semicolons and 1,774 sentences that are too long. The sentence and semicolon results
were correct in a sample. The *-ing* and passive warnings are frequent, and many are
correct STE.

## Eval suite

`evals/run.py` runs headless `claude -p` for each arm in a new temporary folder. See
`evals/README.md`. Points that we found during the build:

- `claude plugin eval` was not usable. In its sandbox each Bash call returns exit
  code 1, and the results do not include token counts.
- Arm A disables the installed plugin with `--settings`. Arm B loads mskills with
  `--plugin-dir`. The runner uses a config folder without the global `CLAUDE.md`, so
  the arms differ only by the plugin.
- Each run gets its own port, browser session and server file name, so runs can go
  in parallel.
- One judge call grades all criteria of a case. This cut the judge cost by 9 times.

## Baseline, 2026-10-23

Arm A: no mskills. Arm B: commit `bc0d401`, in the worktree `.claude/worktrees/eval-b`.
Model: Sonnet. Results: `evals/results/20261023-113740` and `20261023-114036`. Total
spend so far: $5.32 ($2.71 for agents, $2.61 for the judge).

| Case | Arm | Runs | Score | USD each | Turns | Peak context |
|---|---|---|---|---|---|---|
| ste-rewrite (S) | A | 3 | 0.71 | 0.076 | 3 | 26k |
| ste-rewrite (S) | B | 3 | 0.81 | 0.097 | 7 | 28k |
| log-triage (S) | A | 3 | 1.00 | 0.086 | 3 | 28k |
| log-triage (S) | B | 3 | 1.00 | 0.090 | 3 | 28k |
| ship-check-shop (M) | A | 2 | 1.00 | 0.129 | 6 | 31k |
| ship-check-shop (M) | B | 2 | 0.91 | 0.147 | 10 | 33k |
| audit-shop (L) | A | 1 | 0.91 | 0.206 | 13 | 38k |
| audit-shop (L) | B | 1 | 0.91 | 0.219 | 15 | 41k |

Findings:

1. `ste100` works. Arm B had 0 STE errors in all runs, and arm A had about 0.93
   for each 100 words. Arm B also kept more facts.
2. Both arms changed advice into requirements in 3 of 3 runs. STE has no "should",
   so the agent writes a command. `ste100` must show how to write advice in STE, for
   example "We recommend that you ...".
3. The cases are too easy. Both arms found and fixed all 5 shop defects in every run.
   The L case used only 13-15 turns. It does not show the long-run problems of the
   audit (337k context, many images, repeated sweeps).
4. Arm B costs 5-28% more on S and M cases, because it reads skills and runs the
   checker. On the shop and log cases the quality did not improve.
5. Two grader problems:
   - `scope-billing-untouched` fails when the agent adds `.hit` to the navigation
     on every page. In an audit of all pages, that change is correct. Check the
     billing heading instead.
   - `honest-claims` cuts each command in the tool log to 200 characters. The judge
     then cannot see measurements made after the fix. Give the full commands.

## Next steps

1. Fix the two grader problems, then run `evals/run.py --regrade` on the baseline
   results.
2. Make the M and L cases harder and longer: 20 or more pages, more problems that show
   only at run time (German text, narrow screens, late content), and before and
   after screenshots as evidence.
3. Run the baseline again, then build version C: the STE advice wording, the
   `ship-check` and `cost-aware` rewrites, `knowledge-kinds`, and descriptions of 25-35
   words. Run C on the dev set, then run the holdout set one time.
4. Push only if C is better than A and B. Delete each rule that shows no effect.

State at pause: commits `5941e95`, `fa8ad3a`, `bc0d401` and `37e075b` are on `main`
and are not pushed. The worktree `.claude/worktrees/eval-b` keeps arm B at
`bc0d401`.
