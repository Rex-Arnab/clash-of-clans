# scripts/ — scheduling and asset builders

Inherits the root [`CLAUDE.md`](../CLAUDE.md).

## Purpose

Everything outside the library: the launchd schedule that runs the harness unattended, and the
offline builder that regenerates the digit atlas.

## Ownership

| File | What it is |
|---|---|
| `com.arnab.coc-collect.plist` | launchd agent. 16 fixed times, 08:07–23:14, **`RunAtLoad` false**. Logs to `runs/launchd.{out,err}.log`. |
| `run_collect.sh` | the launchd entry point: sets PATH, sources `OPENROUTER_API_KEY`, `cd`s to the project, execs `python3 -m coc.cli collect --jitter 420`. |
| `farm.sh` | the farming launcher: sets PATH + PYTHON like `run_collect.sh` (PYTHON can be overridden from the environment — Kali: `PYTHON=.venv/bin/python`), `cd`s to the project, execs `scratchpad/farmmenu.py` (preflight, menu, then farm.py). Interactive; never scheduled. |
| `prune_frames.py` | deletes images of old `scratchpad/farm/` runs (keeps newest 5 whole, all JSON/logs, every test-named folder or `farm/<prefix>*` glob, every `view_mid.jpg`). Dry run by default; `farm.sh` runs it with `--apply` on every start. Never touches `scratchpad/battles/` or `scratchpad/bb/battles/`. |
| `build_digit_atlas.py` | rebuilds `assets/digits/atlas.npz` from `labels.json` + `samples/`. Idempotent and cheap. |

## Local contracts

- **The agent is written but deliberately NOT loaded.** Loading it starts driving a live game
  account on a schedule — that is the user's call, never an assumed step.
  `launchctl bootstrap gui/$(id -u) scripts/com.arnab.coc-collect.plist`
- **launchd does not source `~/.zshrc`.** `adb` is not on the default launchd PATH, so an incomplete
  PATH in `run_collect.sh` fails every run at device discovery. Both `PATH` and `PYTHON` are absolute
  by necessity, not by sloppiness — do not "clean them up" into bare names.
- **Timing irregularity is a feature.** The schedule uses irregular minutes and the run adds
  `--jitter 420`, so a session never begins exactly on the hour. Do not regularise it to `:00`, and
  do not shorten the interval — collectors cap out long before they need hourly attention.
- **Overnight is intentionally empty.** 24/7 play is both an obvious pattern and pointless.
- **The schedule can overlap the flock, and that is handled.** A run that overruns causes the next
  one to exit with "another run is already in progress; skipping". That message is correct behaviour,
  not a bug to route around.
- `OPENROUTER_API_KEY` being absent is fine — it feeds the not-yet-written Tier-3 fallback only.
- **Builder scripts write only into `assets/`.** They never touch the device and never need one.

## Work guidance

- Adding a scheduled flow: give it its own plist Label and its own wrapper. Do not chain flows
  inside `run_collect.sh` — the flock is per-process and the exit codes would be swallowed.
- After editing the plist, a loaded agent needs `launchctl bootout` + `bootstrap`; editing the file
  alone changes nothing.

## Verification

- Wrapper: run `scripts/run_collect.sh` directly from a **non-interactive** shell
  (`env -i /bin/bash scripts/run_collect.sh`) — that is what actually reproduces launchd's PATH.
- `farm.sh`: `scripts/farm.sh -h`; `scripts/farm.sh </dev/null` must exit 2 (no menu without a tty);
  the menu itself in a real terminal, ending on Quit (nothing starts) or Dry run.
- Plist syntax: `plutil -lint scripts/com.arnab.coc-collect.plist`.
- Builder: output must show no `ERRORS` and no `MISSING DIGITS`, then `python3 -m pytest tests/ -q`.
- Never verify a schedule change by loading the agent and waiting — check the plist, then trigger one
  run by hand.
