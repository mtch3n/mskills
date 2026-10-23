# ASD-STE100 details

Read this file when the core rules in `SKILL.md` do not answer your question. This is
an unofficial summary of Issue 9 (2025). It does not include the official dictionary.

## Word counts

Count each word between two spaces. These items count as one word:

- A number, or a number with its unit: "20 kg".
- An abbreviation or an identifier: "PR-1302", `ste-check.py`.
- Text in quotation marks.
- A title, a heading or a label.
- The name of a person, an organization or a country.

A product name or an API name is a technical name. It counts as its words.

Put text in parentheses into a separate sentence when you can. The checker counts a
parenthesis as one word.

A list item after a colon is a new sentence. The sentence before the colon has its own
limit.

## Verb forms

Use only these forms:

- the infinitive: "to open"
- the imperative: "Open the valve."
- the simple present: "The valve opens."
- the simple past: "The valve opened."
- the simple future: "The valve will open."
- the past participle as an adjective: "the opened valve", "the valve is open"

Do not use the perfect tenses ("has opened", "had opened") or the progressive tenses
("is opening"). Do not use "must" before an instruction, except for safety.

## The passive voice

Ask "who does this?". If you know, name that actor and use the active voice. Use the
passive only in a description when the actor is unknown. Do not use the passive in a
procedure.

## The -ing form

Use an *-ing* word only in a technical name ("routing table") or in a heading. These
words are approved: during, lighting, mating, missing, opening, remaining, routing,
servicing, something.

## Modal verbs

Use "can" for ability or possibility. Use "must" for an obligation. Use "will" for the
future. Do not use "may", "might", "should", "could" or "would".

## Nouns and noun clusters

Use a verb for an action, not a noun made from it: "install", not "do an
installation". Write a noun cluster of three words or fewer. Break a longer cluster
with "of" or a clause: "the timeout value of the connection pool".

## Procedures

Write one instruction in each step. Two instructions are permitted in one sentence
only when the reader does them at the same time.

## Warnings, cautions and notes

- A warning or a caution starts with a clear command. The reason comes after it. Use
  20 words or fewer in each sentence.
- A note gives information. It does not give an instruction. Use 25 words or fewer in
  each sentence.

## Spelling and punctuation

Use American spelling. Do not use contractions or semicolons. All other standard
punctuation is permitted.

## Technical names and verbs

Words that are not in the dictionary are permitted when they are technical names or
technical verbs in the project's subject. Use each one with one meaning. Keep a list of
them in the project and give it to the checker with `--terms`.
