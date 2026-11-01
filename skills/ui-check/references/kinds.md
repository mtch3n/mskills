# ui-check reference

## Kinds

| Line | Kinds | What to do |
|---|---|---|
| `F` fail | `overflow-x`, `clipped`, `overlap`, `control-cut`, `covered-end` | Fix it. A fail is always a defect. Do not report the work as done while a fail stays. |
| `F` fail | `broken-image`, `image-distorted`, `contrast` below the WCAG AA ratio | Fix it. |
| `F` fail | From `--interact`: `focus-invisible`, `focus-clipped`, `focus-covered`, `popup-clipped`, `popup-covered`, `dialog-unreachable` | Fix it. |
| `W` layout | `edge`, `gap`, `row-height`, `row-top`, `row-bottom`, `row-centre`, `icon-centre`, `baseline`, `off-centre`, `sticks-out`, `proximity`, `choice-centre`, `orphan-wrap` | Fix it, or write in the report why it is correct. A gap of 1 to 4 px is almost never correct. |
| `W` components | `inconsistent`, `scale`, `drift`, `off-token`, `double-border`, `cramped-padding`, `control-font`, `target-size` | Fix it, or give the reason. |
| `W` text | `line-length`, `small-text`, `headings`, `truncated`, `early-ellipsis`, `long-label` | Fix it, or give the reason. |
| `W` words | `restates`, `chatty`, `text-heavy`, `wall-of-text`, `long-paragraph` | Remove the text. Do not write it again in other words. |
| `W` tables | `table-column`, `numeric-align`, `empty-cell`, `long-table` | Fix it, or give the reason. |
| `W` cursor | `cursor-lie`, `cursor-mixed` | Fix it, or give the reason. |
| `W` motion | From `--interact`: `focus-shift`, `hover-shift` | Fix it, or give the reason. |
| `S` smell | `card-in-card`, `tinted-box`, `accent-stripe`, `eyebrow`, `subtitles`, `pills`, `border-shadow`, `icon-tile`, `card-grid`, `helper-text` | Compare it with the rules. Remove it if no rule asks for it. |
| `S` smell | `gradient`, `gradient-text`, `glow`, `glass`, `purple`, `emoji`, `hues`, `icon-sets`, `native-tooltip`, `stock-copy`, `filler`, `cursor-zoo` | Compare it with the rules. Remove it if no rule asks for it. |


With `--verbose`, the `layout`, `type`, `shape` and `colour` lines show the values that
the page uses. Many different values for one property show drift.

## Options

- `--width N`, repeat for more. The default is 390 and 1280. `--height N` sets the
  viewport height. The default is 900 px. Use `--width 320 --height 480` for a short
  screen.
- `--stress` makes the text longer, makes names, paths and numbers into long tokens,
  and applies the WCAG text spacing. Then it lists only the new fails.
- `--interact` checks up to 60 Tab stops, hovers over up to 40 visible controls and
  opens up to 15 menus, popups and dialogs.
- `--mode app|marketing|docs` sets the page type for the text checks. The script
  guesses it and prints it after the width. A `docs` page gets no checks for the
  amount of text.
- `--variants` lists each pair of design options that share one layout.
- `--out DIR` gets a framed screenshot, a crop for each finding and the JSON reports.
  The default is `/tmp/ui-check`. `--frame all` draws the box of each element.
- `--baseline DIR` lists what changed since an earlier `--out` folder.
- `--verbose` also prints the layout values, the census and the image paths.
- The exit code is 1 if there is a `fail`.

## Hooks in Claude Code

- If the user asks for an open task on a page, for example "polish the Team page",
  a hook measures the page with `--interact` before you start. It finds the page from
  its name in the message or from the `ui-check:` line in `DESIGN.md`. It gives you
  the problems that are already on the page. Fix them in the same pass.
- After each edit of a UI file, a hook runs `slop-lint` on the lines that you wrote.
- When you stop after you changed UI files, a hook finds the pages that use the
  files and measures them with `--stress --interact`. It finds the pages from a
  `ui-check: <url or file> ...` line in `DESIGN.md`, from the HTML files that use the
  changed files, or from a dev server on this computer and the routes of the changed
  files. On a page that only uses a changed style, it shows only the fails. It gives
  you the problems to fix. It does this up to 3 times for each user message. If it
  cannot measure a page, it tells you.
- The text after `@` in a finding is the CSS rule that sets the value, with its file
  and line.
- When the user's message corrects a UI, a hook tells you to write the rule in the
  rules file.

Other agents do not run these hooks. Run the same commands yourself.

## Other browsers

`scripts/probe.js` is one JavaScript function. It returns the same report and draws
the frame in the page. If a page needs a login, run it in that browser:

- Playwright: `page.evaluate(probe_source, {"frame": "all"})`.
- Any `eval` command: send `(<probe.js text>)({frame: "all"})`.

## Limits

- The script measures the main document only. It does not measure iframes or shadow
  DOM.
- It does not measure loading states, selected states or motion.
- Smells are heuristics. A smell is a question, not an error.

The reasons for the checks are in `docs/ui-check.md` in the repository.
