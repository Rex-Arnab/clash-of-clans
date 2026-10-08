# CLAUDE.md — clash-of-clans automation harness

Binding contract for this repository and everything beneath it. Child `CLAUDE.md` files add local
detail; they never weaken what is written here.

## Purpose

Drive a **real, single, physical Android phone** running Clash of Clans over adb: perceive the
screen with OpenCV, decide what to tap, tap it safely, and record what happened. It is a perception
+ interlock system, not a game client — there is no protocol work and no memory reading.

One device, one account, one game version. Nothing here is written to generalise:

| Fact | Value | Where it is asserted |
|---|---|---|
| Device serial | `EQEMVG6HSOUO9DT4` (Realme RMX5033, Android 16) | `coc/config.py` |
| Transport | Wireless adb, **ephemeral port** — rediscovered via `dns-sd` | `coc/device.py` |
| Game | `com.supercell.clashofclans` 18.600.1 | `coc/config.py` |
| Geometry | landscape **2392x1080**, density **360** | `coc/capture.py:assert_geometry`, `assert_manifest_matches` |

**Every coordinate in this project is native landscape 2392x1080.** There is no scaling step.
If you find yourself converting coordinates, you are doing something wrong.

## Canonical commands

```bash
python3 -m coc.cli status                  # device reachable? battery, screen, game pid
python3 -m coc.cli collect --dry-run       # perceive + decide, send no collection taps
python3 -m coc.cli collect                 # the real run (20-30 s)
python3 -m coc.cli summary --limit 24      # roll up runs/runs.jsonl
python3 -m pytest tests/ -q                # digit reader + defence detector regression gate
python3 scripts/build_digit_atlas.py       # rebuild the atlas after adding samples
```

Unattended farming, either base: `scripts/farm.sh` (menu: mode, priority, plan, battles,
start / dry run) or `scripts/farm.sh gold --max-cycles 3` (no menu) -- see `scratchpad/farmmenu.py`.

Live attacks are not a CLI command yet; they run from `scratchpad/`, one system per base:

```bash
# Home Village — scratchpad/CLAUDE.md: pre-battle checklist, replay, 82-test battle gate
PYTHONPATH=.. python3 -u attack7.py battles/aNN_<date> 2>&1 | tee battles/aNN_<date>/console.log

# Builder Base — scratchpad/bb/CLAUDE.md
python3 -u scratchpad/bb/attack1.py scratchpad/bb/battles/<id> 2>&1 | tee .../console.log
python3 scratchpad/bb/attack1.py /tmp/dry --dry-run        # stops before Find Now!
cd scratchpad/bb && PYTHONPATH=../.. python3 -m pytest test_bb.py -q
```

Python is `/Users/arnabbiswas/.pyenv/versions/3.13.2/bin/python3` (cv2 4.13.0, numpy 2.4.4).
`adb` lives at `/opt/homebrew/share/android-commandlinetools/platform-tools` — not on launchd's PATH,
which is why `scripts/run_collect.sh` sets PATH explicitly.

## Verification gate

Nothing is "done" from code reading. A change to perception, safety, or a flow ships only with:

1. **A measured number and the command that produced it.** Detection margins, read accuracy,
   timings — the table in `TODO.md` is the format and the running record.
2. **A run against the real phone**, named up front. `--dry-run` first, then a live `collect`,
   and quote the resulting `runs/<stamp>_*/run.json`.

If the phone is unreachable, the game is updating, or the density has drifted — **stop and say so.**
A green pytest run is not a substitute; it only covers the digit reader and the detector on two stored frames.

A battle change ships with (a) replay numbers against the previous code (`scratchpad/replay_a10.py`)
and (b) a live battle whose result screen agrees with the tap journal — Lightning used must equal the
zap taps in `rec["taps"]`.

In the **Builder Base** the same rule reads: the regression gate replays stored battle frames
(`scratchpad/bb/test_bb.py`, every case a battle that already went wrong), and a live run's
**"Troops expended" must equal the slots in `rec["stages"]`** — b4 reported a confirmed deploy while
four of seven units sat in hand. One battle never supports a claim about a parameter: damage is
mean 79%, sd 27 over the historical runs, and today's fourteen spanned 29-100% with the same code.

**Progress is judged by bubbles disappearing, never by the resource counters rising.** The account is
near storage cap, so a fully successful collect can move gold by 0.

## Global conventions

- **Fail closed, never improvise.** An unrecognised screen, an ambiguous glyph, or a geometry
  mismatch raises (`DeviceBlocked`, `UnreadableNumber`, `CaptureError`) instead of guessing. A
  plausible-but-wrong action is the expensive failure here, not a stopped run.
- **`DeviceBlocked` is not an error.** Low battery, screen off, game not in front — expected,
  reported, and explicitly *not* retried. It exits `2`; real errors exit `1`.
- **Safety sits below the flows and cannot be opted out of.** See `coc/CLAUDE.md`.
- **Never hardcode the wireless-debugging host:port.** The serial is the only stable anchor.
- **Comments explain the measurement, not the mechanics.** The existing docstrings record *why* a
  threshold or bound is that number ("measured: a correct '1' scored 0.750"). Match that.
- Do not add a config loader, a plugin system, or a device abstraction. One device, one account.

## Base scoping — one base per task, never edit the other one's files

The Home Village and the Builder Base are **different screen spaces, different armies and different
flows**, developed in separate sessions. Name the base being worked on before the first edit.

**DO NOT modify a file that belongs to the other base.** A Builder Base task never edits
`scratchpad/attack7.py` or `coc/flows/home_collect.py`; a Home Village task never edits
`coc/builder_base.py` or `assets/bb_defenses.json` — not to tidy it, not to share a helper, not
because a constant looks wrong there. Report what you noticed and leave it untouched. If a task
genuinely cannot be done without touching the other base's file, **stop and ask first.**

**Scoping restricts editing, never reuse.** Importing, running and reading everything in the repo
stays encouraged — that is what the shared foundation is for. Builder Base work should stand on the
existing perception stack as-is: `locate.deploy_targets()` and the stage-0 YOLO detector
(`coc/vision/yolo.py`, `assets/models/`), the digit reader, `capture`, `device`, the `Tapper`,
`scripts/`, and the `scratchpad/` probe and diagnostic helpers. Reading the Home Village code and
`scratchpad/knowledge/doctrine.md` for reference is fine too. Only *changing* the other base's files
is out of bounds — if a Home Village helper needs different behaviour for the Builder Base, copy it
into a Builder Base module or add alongside it, do not edit it in place.

| Scope | Files |
|---|---|
| **Home Village only** | `coc/flows/home_collect.py`; `coc/battle.py` (multiplayer entry, `ATTACK_BUTTON`, `in_battle`); `safety.NO_TAP_ZONES`; the whole live attack system in `scratchpad/` — `attack*.py`, `strategy.py`, `zaps.py`, `targets.py`, `spots.py`, `camera.py`, `hud.py`, `loot.py`, `cardstate.py`, `waves.py`, `deploy_plan.py`, `recorder.py`, `replay_*.py`, `test_battle_clock.py`, `test_spots.py`, `cards/`, `battles/`, `knowledge/doctrine.md` |
| **Builder Base only** | `coc/builder_base.py` (`BB_NO_TAP_ZONES`, `BB_BATTLE_NO_TAP`, the zoom-tolerant bubble finder, BB deploy planning); `assets/bb_defenses.json`; any new Builder Base flow, script or scratchpad module |
| **Shared foundation** | `coc/config.py`, `coc/device.py`, `coc/capture.py`, `coc/safety.py` (the `Tapper` itself), `coc/report.py`, `coc/cli.py`, `coc/vision/`, `assets/digits/`, `assets/templates/`, `assets/models/`, `scripts/`, `tests/` |

- **Shared-foundation edits are additive and must leave the other base's behaviour identical.**
  Add a new zone list, a new constant, a new function — never repurpose an existing one. Say in the
  summary which shared file was touched and why the other base is unaffected, and run the other
  base's gate: `python3 -m pytest tests/ -q`, plus the 82-test battle gate in `scratchpad/` when the
  edit touches anything `attack7.py` imports.
- **Never generalise the two into one path.** No base abstraction, no shared coordinate, no reused
  no-tap zone list, no "works for both" flow. A Home Village constant in Builder Base code is a bug
  even when it happens to work — see `coc/flows/CLAUDE.md` "Builder Base contracts".
  This is about **screen-space facts** — coordinates, zones, HUD boxes, zoom, army — not about the
  shared perception stack, which both bases are meant to use.
- **`TODO.md` entries name the base.** A measured number, a threshold or a battle record without
  "Home Village" / "Builder Base" on it is unusable in the next session.

## Repo layout

| Path | What it is |
|---|---|
| `coc/` | the package — transport, capture, safety, logging, CLI, battle helpers |
| `coc/vision/` | perception: digits, templates, screen classification |
| `coc/flows/` | game behaviours built on the layers above |
| `assets/` | templates, digit atlas and detector weights — the perception ground truth |
| `scripts/` | scheduler entry points and the atlas builder |
| `tests/` | regression gates for the digit reader and the local defence detector (see `assets/CLAUDE.md` for the ground truth they read) |
| `scratchpad/` | the live Home Village attack system (`attack7.py` + modules), its offline replay and battle tests, and every battle's recorded evidence under `battles/`. NOT landed in `coc/`. |
| `scratchpad/bb/` | the live **Builder Base** attack system (`attack1.py`, `bbspots.py`, `bbtap.py`), its regression gate and `battles/` evidence. Separate from the Home Village system by the base-scoping rule above; it reuses `coc/` but shares no coordinate with it. |
| `runs/` | **generated.** Append-only `runs.jsonl` + per-run dirs. Never hand-edit; screenshots are pruned to the last 40 runs by `coc/report.py`. `.run.lock` is the single-run flock. |

`TODO.md` is the running task log and the measured-numbers record. **It, not `CLAUDE.md`, is where
work in progress and findings go.** Update it when a task completes.

## Child DOX Index

- [`coc/CLAUDE.md`](coc/CLAUDE.md) — package core: device, capture, safety, report, CLI
- [`coc/vision/CLAUDE.md`](coc/vision/CLAUDE.md) — perception layer
- [`coc/flows/CLAUDE.md`](coc/flows/CLAUDE.md) — game flows
- [`assets/CLAUDE.md`](assets/CLAUDE.md) — templates and digit atlas
- [`scripts/CLAUDE.md`](scripts/CLAUDE.md) — scheduling and asset builders
- [`scratchpad/CLAUDE.md`](scratchpad/CLAUDE.md) — the live Home Village attack system
- [`scratchpad/bb/CLAUDE.md`](scratchpad/bb/CLAUDE.md) — the live Builder Base attack system
