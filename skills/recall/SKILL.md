---
name: recall
description: Finds every past Claude Code session about one task, pulls that task out of them, fact-checks what was said and done about it against the real files, git and tools, and writes a focused brief plus a handoff prompt for a fresh session. Use when the user asks to recall, reconstruct, cut a task out of a session, find the sessions where something was worked on, or continue one thread from earlier work.
disable-model-invocation: true
---

# Recall

A session can do many things, and one task can spread over many sessions. This skill
rebuilds the context for **one** task from all of them and checks it, so the next step starts from what is true, not from what a summary
or an earlier agent claimed.

The script is `scripts/session-timeline.py` in this skill's base directory. Run it
with `python3 -I`.

## 1. Pin the task

Take the task from the user's words. If they didn't name one, ask which task, and
stop. If the user pasted a summary or handoff prompt, it's one more source of
claims, every one counted as **agent said** until checked. A session's first message
can be such a handoff too: if it reads like one agent briefing another, treat it the
same way, even though it's recorded as typed by the user.

## 2. Find every related session

Unless the user named the sessions, search for them. Pick 2 to 4 words specific to
the task (names of files, features, commands, branches) rather than common ones:

```bash
python3 -I <base>/scripts/session-timeline.py --find "<words>"
```

That searches the current folder and its `.claude/worktrees/*` sessions, ranked by
how many of the words matched, then by hits. `(this session)` counts too. If nothing
relevant comes back, or the task clearly spans repos, widen it with `--all` (every
project; takes a few seconds).

Keep every session that is actually about the task: high hits, a matching title or
first prompt. Drop ones that only mention a word in passing. Say the task and the
sessions you kept, one line each with date and title, before reading. Ask only if
you can't tell which sessions belong.

## 3. Read with the session-reader agent

Spawn `mskills:session-reader` with the task in the user's words, the session ids
and the script's full path. For more than two sessions, spawn one reader per session
in parallel. Each returns the task's claims sorted into user said, agent said, done,
superseded and open. Merge them by time: a later session's decision supersedes an
earlier one's. Don't read the raw timelines in the main session; keeping them out is
the point.

## 4. Check every claim

Check each **done** and **agent said** claim yourself against the real state:
files, `git`, `gh`, installed tools, a test or command run. Use the reader's CHECKS
as a starting point, not as proof. One claim, one check. Tag each:

- `[verified]` checked and true now
- `[wrong]` checked and false; say what is actually there
- `[unverified]` can't be checked from here; say why
- `[user said]` a decision quoted from the user; it still stands unless superseded
- `[agent said]` decided or asserted by an agent and never confirmed by the user

A claim that's true on disk but rests on an agent's decision gets both tags:
`[verified] [agent said]`.

## 5. Write the brief

```
Recall: <task> · from <session ids> · <N> claims checked

Goal
> the user's own words

Where it stands
- up to 5 bullets of verified state

Claims
| tag | claim | checked with |

Decisions to keep
- [user said] ones that still stand, newest wins

Needs your call
- [agent said] decisions the user never confirmed
- [wrong] claims and what to do about them

Left behind
- other tasks in the session, one line each, only if they touch this one

Next step
- the single next action
```

Then a **handoff prompt**: a self-contained paragraph the user can paste into a new
session to carry on this task alone. It holds only verified state, the user's
decisions in their own words, and the open items. No `[wrong]` claim, no unconfirmed
agent decision presented as settled.

Stop after the brief. Don't start the next step until the user says so.
