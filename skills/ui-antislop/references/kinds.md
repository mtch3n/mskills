# ui-antislop reference

## Kinds

| Line | Kinds | What to do |
|---|---|---|
| `F` fail | `overflow-x`, `clipped`, `overlap`, `control-cut`, `covered-end` | Fix it. A fail is always a defect. Do not report the work as done while a fail stays. |
| `F` fail | `broken-image`, `image-distorted`, `contrast` below the WCAG AA ratio | Fix it. |
| `F` fail | From `--interact`: `focus-invisible`, `focus-clipped`, `focus-covered`, `popup-clipped`, `popup-covered`, `dialog-unreachable` | Fix it. |
| `W` layout | `edge`, `gap`, `row-height`, `row-top`, `row-bottom`, `row-centre`, `icon-centre`, `baseline`, `off-centre`, `sticks-out`, `proximity`, `choice-centre`, `orphan-wrap` | Fix it, or write in the report why it is correct. A gap of 1 to 4 px is almost never correct. |
| `W` components | `inconsistent`, `card-actions`, `nested-radius`, `scale`, `drift`, `off-token`, `double-border`, `cramped-padding`, `control-font`, `target-size` | Fix it, or give the reason. |
| `W` text | `line-length`, `small-text`, `tight-text`, `headings`, `truncated`, `early-ellipsis`, `long-label` | Fix it, or give the reason. |
| `W` words | `restates`, `chatty`, `text-heavy`, `wall-of-text`, `long-paragraph` | List it for the user. Do not change the text. |
| `W` tables | `table-column`, `numeric-align`, `empty-cell`, `long-table` | Fix it, or give the reason. |
| `W` cursor | `cursor-lie`, `cursor-mixed` | Fix it, or give the reason. |
| `W` motion | From `--interact`: `focus-shift`, `hover-shift` | Fix it, or give the reason. |
| `S` smell | `card-in-card`, `tinted-box`, `accent-stripe`, `eyebrow`, `pills`, `border-shadow`, `icon-tile`, `card-grid`, `heavy-heading` | Compare it with the rules. Remove it if no rule asks for it. |
| `S` smell | `gradient`, `gradient-text`, `glow`, `glass`, `purple`, `hues`, `icon-sets`, `native-tooltip`, `cursor-zoo`, `motion` | Compare it with the rules. Remove it if no rule asks for it. |
| `S` words | `subtitles`, `helper-text`, `shouting`, `emoji`, `stock-copy`, `filler` | List it for the user. Do not change the text. |


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
  The default is `/tmp/ui-antislop`. `--frame all` draws the box of each element.
- `--baseline DIR` lists what changed since an earlier `--out` folder.
- `--verbose` also prints the layout values, the census and the image paths.
- The exit code is 1 if there is a `fail`.

## Hook in Claude Code

- After each edit of a UI file in a git repository, a hook runs `slop-lint` on the
  lines that you changed.
- The text after `@` in a finding is the CSS rule that sets the value, with its file
  and line.

Other agents do not run this hook. Run `slop-lint` yourself.

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

The reasons for the checks are in `docs/ui-antislop.md` in the repository.
