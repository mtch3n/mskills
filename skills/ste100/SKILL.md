---
name: ste100
description: Writes English in ASD-STE100 Simplified Technical English and rewrites dense or ambiguous English into it. Use for reports, handoffs, instructions, docs, commit and PR text, or when asked for STE.
---

# ASD-STE100

Write so that a reader who cannot ask you a question does the correct thing. This is an
unofficial summary of ASD-STE100. It is not affiliated with ASD and does not certify
compliance.

## Scope

Apply these rules to English prose. Do not change code, commands, paths, identifiers,
error text, quoted words or other languages.

## Meaning first

A rewrite must keep the meaning. Do not do these things:

- Do not make a statement stronger or weaker. "Can fail" does not become "fails".
- Do not invent an actor to remove a passive. If you do not know who did it, keep the
  passive in a description.
- Do not drop an object, a condition, a number or a limit.
- Do not add a prohibition or a step that the original does not have.

If a rule and the meaning conflict, keep the meaning and tell the reader which rule
you did not apply.

## Advice is not a command

STE has no "should" or "may". Do not change advice into a command to remove them.
"Advisable", "ideally", "ought to", "should" and "it is a good idea" are advice. Write
advice with "we recommend":

- "Ideally, tell #ops." becomes "We recommend that you tell the #ops channel."
- "Flags ought to stay for 48 hours." becomes "We recommend that flags stay for at
  least 48 hours."

In a procedure, keep a recommended step out of the required steps. Put it in its own
list, or start the step with "We recommend that you". "Must", "has to", "is supposed
to" and "only" are requirements. Keep them as commands.

## Core rules

1. Write one instruction or one topic in each sentence.
2. Write a condition before its instruction: "If the test fails, stop the release."
3. Start a procedure step with a verb in the imperative: "Open the file."
4. Use the active voice. Use the passive only in a description when the actor is
   unknown.
5. Use only the simple present, simple past and simple future. Do not use "has
   done", "is doing", "may", "should", "could" or "would".
6. Do not use contractions, phrasal verbs or *-ing* verb forms.
7. Use one word for one thing, every time. Keep "the" and "a".
8. Use 20 words or fewer in a procedure sentence. Use 25 words or fewer in a
   description sentence. Use 6 sentences or fewer in a paragraph.
9. Do not use semicolons.
10. Write a warning as a command, then give the reason. Only a requirement in the
    original is a warning. Advice with a risk as its reason stays advice:
    "We recommend that you do X. If you do not do X, Y can occur."

For word counts, verb forms, approved *-ing* words, noun clusters and notes, read
`references/rules.md`.

## Check

Run the checker before you send the text:

```bash
python3 -I <base>/scripts/ste-check.py [--terms <file>] [--procedure] <file>
```

- Fix every error.
- Read every warning. Some warnings are correct STE, for example a technical name with
  *-ing*.
- If the project has a list of its technical names, give it with `--terms`. Use one
  name on each line.
- Use `--procedure` when all the text is steps.
- Stop after two passes. Report the errors that remain.

The checker does not examine word meaning, noun clusters or ambiguity. Read for these
yourself.

## Example

Before:

> Once the migration has been kicked off, it's important that any lingering
> connections to the legacy DB are drained; ideally this should be verified via the
> dashboard.

After:

> The migration can stop if connections to the old database stay open.
>
> 1. Start the migration.
> 2. Close all connections to the old database.
>
> We recommend that you look at the dashboard to make sure that the number of
> connections is 0.
