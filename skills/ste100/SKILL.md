---
name: ste100
description: Writes English in ASD-STE100 Simplified Technical English and rewrites dense or ambiguous English into it. Use when writing English that a person or another agent will act on (reports, status updates, handoff prompts, worker briefs, instructions, docs, PR and commit text), and when asked to simplify, clarify or rewrite text into STE or ASD-STE100.
---

# ASD-STE100

ASD-STE100 (Simplified Technical English) is a controlled language from the aerospace
industry. Each word has one meaning, each sentence has one job, and the reader never has
to guess who does what. Use it so a reader who cannot ask you a question still acts
correctly.

## What it covers

Apply it to English prose only. Keep these as they are:

- Code, commands, paths, identifiers, config keys, error text and log lines.
- Product names, API names and other technical names. Each counts as one word.
- Words quoted from the user or a source.
- Text in other languages.

## Rewrite

Do these steps on each sentence.

1. **Sort it.** A *procedure* tells the reader to do something. A *description* tells the
   reader what a thing is or what it does.
2. **Split it.** Write one instruction per sentence and one topic per sentence. Put a
   condition before its instruction: "If the test fails, stop the release."
3. **Fix the verbs.**
   - Use the active voice. Name who does the action.
   - Use the simple present, simple past or simple future. In a procedure, start with
     the verb: "Open the file."
   - Do not use an *-ing* form as a verb. "The script is checking the file" becomes
     "The script checks the file."
   - Do not use phrasal verbs. "Set up the server" becomes "Install the server" or
     "Configure the server."
   - Use the verb, not a noun made from it. "Do an installation of" becomes "Install."
4. **Fix the words.**
   - Use one word for one thing, every time. Do not change words to sound less
     repetitive.
   - Use the simplest common word with one meaning. Do not use idioms or slang.
   - Keep articles ("the", "a") and the small words that show structure. Do not delete
     words to make a sentence shorter.
   - Replace "it", "this" and "that" with the noun when the reader could pick the wrong
     one.
5. **Fix the structure.**
   - Write a noun cluster of three words or fewer. Break a longer one with "of" or a
     clause: "server connection pool timeout value" becomes "the timeout value of the
     connection pool."
   - Put steps in a numbered list, one action per step.
   - Write a warning as a command first, then the reason: "Do not delete the branch. It
     holds the only copy of the fix."

## Limits

| Rule | Limit |
|---|---|
| Sentence in a procedure | 20 words |
| Sentence in a description | 25 words |
| Paragraph | 6 sentences, one topic |
| Noun cluster | 3 words |
| Semicolon | not permitted. Write two sentences. |
| Verb tense | simple present, simple past, simple future |

## Check

Run the checker on what you wrote before you send it:

```bash
python3 -I <base>/scripts/ste-check.py <file>
echo "<text>" | python3 -I <base>/scripts/ste-check.py
```

It reports errors for sentence length, paragraph length and semicolons, and warnings
for phrasal verbs, *-ing* forms and passive voice. Fix every error. Read each warning:
the passive voice is correct in a description when the actor is unknown or not
important, and an *-ing* word is correct in a technical name. The checker cannot judge
noun clusters, word meaning or ambiguity. Read for those yourself.

## Example

Before:

> Once the migration has been kicked off, it's important that any lingering connections
> to the legacy DB are drained, otherwise the cutover could potentially end up being
> blocked; ideally this should be verified via the dashboard.

After:

> The migration stops if connections to the old database stay open.
>
> 1. Start the migration.
> 2. Close all connections to the old database.
> 3. On the dashboard, make sure that the number of connections is 0.

## The dictionary

The full standard includes a dictionary of approved words, each with one meaning and
one part of speech. This skill does not include it. To check a word, get the current
specification free from the ASD-STE100 maintenance group (asd-ste100.org). Without it,
follow the rules above and choose the most common word with one clear meaning.
