# Evals

These evals measure if the mskills skills make an agent better or cheaper. Each case
runs a headless `claude -p` in a new temporary folder, one time for each arm. An arm is
the agent with no mskills plugin, or the agent with mskills loaded from one folder.

## Run

```bash
python3 -I evals/run.py --arm A --arm B=/path/to/mskills [--case NAME] [--set dev|holdout|all] [--tier S|M|L] [--runs N] [-j JOBS]
python3 -I evals/run.py --regrade evals/results/<timestamp>
```

- Arm `A` (no path) disables the installed `mskills@mskills` plugin.
- Arm `NAME=PATH` loads the plugin from `PATH`. Use a git worktree to test an older
  commit.
- The agent runs with `--permission-mode bypassPermissions` in a folder under `/tmp`.
  It runs as you. Use only cases from this repository.
- `--regrade` grades the results again with the current graders. It does not run the
  agents again.

Results go to `evals/results/<timestamp>/`: one folder for each case, arm and run, with
the final reply, the diff, the transcript and `result.json`. `summary.md` gives the mean
score, cost, turns, peak context, cache reads and images for each case and arm.

## Cases

| Case | Tier | Set | What it measures |
|---|---|---|---|
| `ste-rewrite` | S | dev | STE errors, kept facts and kept strength in a rewrite |
| `log-triage` | S | dev | Root causes in a 20,000-line log, without reading the whole log |
| `ship-check-shop` | M | dev | Defects found and fixed, and traps avoided, in a web change |
| `audit-shop` | L | dev | The same site, all pages and sizes, over a long run |
| `ui-complaint` | M | dev | A short UI complaint. Checks the named fix, the same bug on a page that the user did not name, the scope and the rules in `DESIGN.md`. Graded with `ui-check`, so it needs `uv`. |
| `ui-slop-dashboard` | M | dev | A vague complaint about a dashboard that looks generated. Checks that the slop on the dashboard goes, that the sidebar icons are centred on every page, that the numbers stay, and the rule. Needs `uv`. |
| `ui-render-only` | M | dev | A UI complaint whose causes show only on the rendered page. Chips sized in `em` differ by context. On a phone, a long link pushes the Copy button out of its box. Checks the fix, the same bug on another page, a longer link, the scope and the rule. Needs `uv`. |
| `ui-polish` | M | dev | "Polish the Team page" with no defect named. The page has 7 defects that the agent must find. Examples are uneven chips, a hidden Copy button on a phone and no focus style. Checks each fix, the content, the scope and new problems. Needs `uv`. |
| `ship-check-cli` | M | holdout | Defects found and fixed, and traps avoided, in a CLI change |
| `ste-holdout` | S | holdout | The same as `ste-rewrite`, with a different text |

Do not look at holdout results while you change a skill. Run them one time at the end.

## Add a case

Make `cases/<name>/` with these files:

- `case.json`: `prompt`, `tier`, `set`, `runs`, `max_turns`, `timeout`, and `fixture`
  if the files come from `fixtures/`.
- `fixture/`: files that are copied into the work folder.
- `setup.py` (optional): runs in the work folder before the agent starts.
- `grade.py`: a `grade(run)` function that returns a list of
  `{"name", "passed", "weight", "detail", "metrics"}`. Use `run.workdir`, `run.final`,
  `run.diff`, `run.calls` and `run.judge({name: criterion}, evidence)`.
