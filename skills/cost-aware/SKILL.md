---
name: cost-aware
description: How an agent keeps its token cost down while doing the same work. Use before a long or repetitive task (sweeps, audits, many files, long test or CI runs), before reading images, screenshots, large logs or big command output, before waiting on something slow, before spawning workers or subagents, and when a session's context has grown large.
---

# Cost aware

Every turn re-reads the whole conversation. So cost is roughly **context size ×
number of turns**, and anything that enters the context is paid for again on every
turn after it. Output and one-off reads are small next to that. Keep the context
small and the turns few.

## Keep big things out of the main context

- **Hand heavy reading to a subagent.** Images, screenshots, long logs, large diffs
  and wide searches go to a subagent that returns a short text answer: what it
  found, with file paths. The main context never holds the raw material.
- **Read text before pixels.** A DOM, an accessibility tree, a layout dump, JSON or
  a test result answers most questions for a fraction of an image. Look at an image
  only for what text can't show.
- **Read the part you need.** Filter command output (`grep`, `tail`, `jq`, a line
  range) instead of reading it whole. Save big output to a file and read slices.

## Spend fewer turns

- **Don't poll.** Run a long job in the background and let it notify you once when
  it ends. No "still waiting" turns, no `sleep` loops.
- **Small run first.** Before a long run, run one case end to end and check its
  result. A long run that fails at minute 40 on a setup problem is paid for twice.
- **Script the repeat.** A step you'll do more than twice becomes a script. Keep it
  where the next session can find it (the repo, or the skill that needs it) so it
  isn't rebuilt.
- **Batch independent calls** in one turn instead of one per turn.

## Do less work

- **Cut the scope that can't change the result**: a configuration the product
  doesn't support, a platform it doesn't ship on, a case already covered.
- **Get the rules before the work.** Ask or read the constraints first; work redone
  because a rule was guessed costs the whole task again.
- **One job per context.** New scope that arrives midway goes to a new worker or a
  new session, not onto a context that's already large.
- **Stop when it's done.** Report and stop; don't keep a session alive to watch.

## Match the worker to the job

- Mechanical steps (capture, walk, compare, count): a script, no model.
- Scanning and sorting (read these files, list the hits): a cheaper, faster model.
- Judgment (decide, design, fix, review): the main model.

## When context is already large

Finish the current step, write down the state (files, commit, a handoff note), and
continue in a fresh session or after compacting, rather than carrying the old
context through the next task.
