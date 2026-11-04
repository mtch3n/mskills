# ui-antislop: why it measures

## The problem

On 2026-10-31 we read about 5,000 UI prompts from the user's Claude Code history. The
prompts came from four groups of projects: marketing sites, apps, internal dashboards
and a desktop app. Cheap Sonnet scouts read the prompts and sorted each complaint into
a class. Each scout found the same five problems.

1. **Rules ignored.** This was the largest class. The agent wrote raw colors instead
   of tokens, wrote its own component instead of the library component, let a brand
   color leak into other screens, and guessed the numbers of a reference site.
2. **Slop patterns.** A card inside a card, a card around one item, a colored stripe
   on one side, a small label above a heading, a box with a fill and a border,
   gradients, glows, emoji, many badges, many hues and a helper sentence under each
   heading.
3. **Geometry.** Page widths and paddings that are different on each page, table
   headers that do not align with their cells, icons that are not centered on their
   label, and edges that are 1 to 4 px apart.
4. **Scope.** The agent changed or removed parts that the user did not name. The
   user's decisions were only in the chat, so the next session lost them.
5. **One instance only.** The agent fixed the instance in the screenshot. The same
   problem stayed on the other pages.

The user often sent one screenshot and one line, and the screenshot often showed more
than one defect. After two or three repeats, the user wrote the rule as an order.

## The design loops

A second scout read the full transcripts of 14 long UI loops, in which the user asked
for the same change three or more times. Most of these loops were about the design,
not about pixels. The causes, with the number of loops:

1. The agent invented a look with no reference, and its "options" were one layout
   in different colors (7).
2. The agent forgot a rule from an earlier message, for example "use the default theme" or
   "no card inside a card" (6).
3. The agent added helper text, tabs, screens or decoration that nobody asked for (6).
4. The agent read the request incorrectly or invented a term (5).
5. The fix covered one instance, or nobody checked it in the real app (4).
6. The user did not find the mockup, or got a process report instead of a fix (4).

A loop was long when the request said "redesign", "more professional" or "AI slop"
with no reference, and when the user wrote "still" or "again". The loops stopped when
the user wrote the structure or the rule, when the agent made the rule into a test,
or when the agent measured the real screen.

Thus the plugin has three parts:

- `ui-design` is the procedure for causes 1 to 4 and 6. It requires a reference,
  options that differ in structure, a checklist of the rules, and no additions that
  nobody asked for.
- `slop-lint.py` checks the source after each edit. Rules about tokens and slop
  become a test, which stopped one of the loops.
- `ui-antislop.py` measures the rendered page. `--variants` finds options that share
  one layout.

The hooks start the steps when the agent forgets them. In the first eval, the agent
did not load the skill because it fixed the bug from the CSS alone.

## What designers and other tools check

Design QA checklists use this order: layout and hierarchy, type, color, components
and states, content states, responsive, then a decision for each finding. The
measurable rules from WCAG 2.2 and the design systems that `ui-antislop` now uses:

| Rule | Limit | Kind | Source |
|---|---|---|---|
| Target size | 24 × 24 px, or no other target within the 24 px circle | `target-size` | WCAG 2.5.8 |
| Line length | Near 45 to 75 characters. The check reports more than 90. | `line-length` | Design QA and type guides |
| Minimum text size | 12 px | `small-text` | Lighthouse uses 12 px |
| Heading order | One `h1`, no skipped level | `headings` | axe `heading-order` |
| Border and wide shadow | Do not use both on one box | `border-shadow` | Slop lists |
| Icon tile above a heading | Do not use | `icon-tile` | Slop lists |
| Row of identical icon cards | Do not use | `card-grid` | Slop lists |

Linters for design systems (stylelint strict values, the Primer and Atlassian
plugins, the Tailwind plugin) all report raw values in place of tokens. `slop-lint`
does the same for colors and sizes. Like those linters, it lets the project permit a
rule. The reason goes in `DESIGN.md`.

We did not find a tool that measures edges of siblings, gaps, table columns or
clipped text on the rendered page. Overflow, contrast and target size are common.
Studies of vision models agree with the transcripts: the models are weak at fine
alignment and spacing.

These checks stay a judgment of the human or the agent: hierarchy (the squint
test), one primary action, grouping, color meaning (the grayscale test), brand fit,
and copy. `ui-design` turns some of these into questions to ask before the build.

Sources:

- WCAG 2.2 target size: https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html
- Design QA checklist: https://21st.dev/blog/design-qa-checklist
- Lighthouse tap targets: https://developer.chrome.com/docs/lighthouse/seo/tap-targets
- axe rules: https://github.com/dequelabs/axe-core/blob/develop/doc/rule-descriptions.md
- Atlassian lint rules: https://atlassian.design/components/eslint-plugin-design-system/usage
- Primer stylelint: https://github.com/primer/stylelint-config
- Figma Design Lint: https://github.com/destefanis/design-lint
- Polypane overflow: https://polypane.app/docs/horizontal-overflow/
- UICrit, critiques of UIs by models: https://arxiv.org/pdf/2407.08850

## Other UI skills

Two other skills are often installed with this plugin: impeccable and
design-taste-frontend. We read both on 2026-10-31.

- Both choose a direction and a style, and both review the result with the model
  that reads its own screenshots. Both have source and page detectors for slop.
- Neither measures the edges of siblings, gaps, table columns, icon centers, clipped
  text, rows of chips, the differences between pages, or a baseline. `ui-antislop`
  does these.
- Neither records the user's corrections, and neither stops the agent when it did not
  measure.

Some of their rules disagree. impeccable keeps card radii at 12 to 16 px and permits
a soft shadow. design-taste-frontend calls one 12 to 16 px radius on everything a
tell, fails resting shadows and thin borders, and fails a page with little motion.
These rules are for marketing pages. On an app screen they conflict with the borders
and the quiet surfaces that the app needs. Thus the project's `DESIGN.md` wins, and
an app screen does not get the marketing rules.

## Detail defects

We asked two other models for the detail defects that designers see and that
generated UIs get wrong: Codex and Gemini 4 Argon through Antigravity. They gave 48
and 44 items, and about 70% of the items were the same. From their lists we added:

- On the page at rest: `double-border`, `cramped-padding`, `control-font`,
  `image-distorted`, `choice-centre`, `proximity`, `early-ellipsis`, `covered-end`,
  `control-cut`, and the cursor checks.
- With `--stress`: longer text, long tokens and the WCAG text spacing. Many
  overflow defects show only with real content.
- With `--interact`: focus that is not visible, clipped or covered, and layout that
  moves on hover or focus.

- With `--interact`, also open menus, popups and dialogs: a popup that its container
  or the screen cuts off, a popup under other content, and a dialog taller than the
  screen that does not scroll. A full-screen backdrop is not a popup.
- On the page at rest: one item alone on the last line of a row that wraps
  (`orphan-wrap`).

Loading states and selected states are not measured yet.

In the third eval run, the agents with the plugin ran `ui-antislop.py` 2 or 3 times
and did not give `--stress` or `--interact`. Thus the skill now gives both options in
the main command.

In the first holdout run, the agents with the plugin got a lower score and used two
times the cost of the agents with no plugin. There were three causes:

- The baseline list did not have 2 of the 6 defects. The agents fixed only the
  items on the list and did not look for more. Thus the baseline now tells the agent
  that the list is not complete.
- The Stop hook stopped the agent again for warnings. Thus it now stops the agent
  only for a new fail or a new `slop-lint` finding.
- In a project with no page to render, the Stop hook told the agent to measure. The
  agent used many turns and did not get a measurement. Thus the hook now runs only
  `slop-lint` when it finds no page.

The two holdout cases are now known. A fair test needs new holdout cases.

The Stop hook is removed. In the real sessions of 1 to 4 November, it stopped the
agent about 400 times. Almost all of these stops were for `slop-lint` findings, not
for fails. In one session it stopped the agent 92 times. Each stop made the agent
continue after its final reply. Thus the reply moved off the screen while the user
read it.

In the evals, the agent did fix the items after a stop. But it also checked the page
again with its own tools and wrote its report again. Feedback now
comes only while the agent works: the lint after each edit and the baseline before
the work.

The correction hook matched words such as "stop", "again" and "why". It added the UI
steps to prompts that were not about a UI. It now needs a word for a visible defect,
for example "misaligned", "too big" or "cut off", and a word for a part of a UI.

## Too much text

The user's history has 86 prompts about text, for example "not useful", "too
verbose" and "remove this text". The text checks measure:

- A sentence under a heading that repeats the heading (`restates`), or any helper
  sentence on an app screen (`helper-text`).
- Filler phrases (`filler`) and long labels (`long-label`).
- Long paragraphs, runs of prose taller than a screen, and screens that are mostly
  text with no pictures (`long-paragraph`, `wall-of-text`, `text-heavy`, `chatty`).

The limits depend on the page type. A docs page gets no checks for the amount of
text.

## Why numbers and not a screenshot

The transcripts show that the agent did look at its screenshots. It still reported
"holds up" for screens that the user then rejected. A model that reads a screenshot
does not see a 2 px step reliably. The browser knows the exact position of each box,
so `probe.js` reads the positions and reports the step as a number.

The frame image is for the human. It also helps the agent look at one finding. It
is not the check. One cropped image costs much less than a full page, so the script
writes a crop for each finding.

## How the checks avoid noise

A check that reports too much is not used. These rules keep the checks quiet:

- Only visible edges count: text, images, fields, and boxes with a fill, a border or a
  shadow. The edges of an empty wrapper do not count.
- An edge finding needs a near miss: two edges that are 1 to 4 px apart. Edges that
  are equal, or far apart, are a decision.
- The probe compares two boxes only if they are in the same visible container. It
  compares text in two containers only if the containers align. Thus it does not
  compare a tab button inside a padded tab bar with a card outside the bar.
- The probe does not compare the left or right edges of two items that have the same
  center.
- A gap finding needs a stack or row in which one gap value occurs two or more times,
  and a different gap that occurs one time.
- Text cut short with an ellipsis is one warning for the page, not one for each cell.
- The probe ignores hidden text, for example screen-reader labels.

We tuned these rules on the shadcn example pages (dashboard, tasks, authentication).
After these changes, these pages give no fail. The warnings that stay are real, for
example trend icons that are 2 px above the center of their label, and sortable table
headers that are 2 px to the left of their cells.

## Limits

- The script measures the page at rest, in the main document. It does not measure
  hover, focus, open menus, motion, iframes or shadow DOM.
- Smells are heuristics. The project's rules decide if a smell is a problem.
- The eval case `ui-complaint` tests the skill with Claude Code. Other agents need a
  separate test.
