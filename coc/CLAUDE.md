# coc/ — package core

Inherits the root [`CLAUDE.md`](../CLAUDE.md).

## Purpose

The layers everything else stands on: adb transport, frame acquisition, the tap interlock,
run logging, and the CLI the scheduler invokes.

## Ownership

| Module | Owns |
|---|---|
| `config.py` | every device/account/geometry constant. Plain module of constants, deliberately not a file loader. |
| `device.py` | adb: discovery, reconnection, shell, power state, raw input. |
| `capture.py` | `Frame` (BGR ndarray, exactly `CAPTURE_H x CAPTURE_W`), geometry assertions, waiting for the game to be genuinely in front. |
| `safety.py` | the no-tap zones and `Tapper`. The only sanctioned way to tap. |
| `report.py` | `RunLog` — JSONL line per run, screenshots, retention pruning. |
| `battle.py` | battle-side helpers: high-rate raw frame capture, `in_battle()`, troop-card deploy detection, multiplayer entry. Decides nothing about WHERE to deploy. |
| `builder_base.py` | Builder Base: HUD/no-tap zones, zoom-tolerant loot-bubble finder, battle boundary hull, deploy planning, dialog recovery, card state, defence knowledge base loader. A DIFFERENT screen space from the Home Village — never reuse `safety.NO_TAP_ZONES` there. |
| `cli.py` | argument parsing, the run flock, exit codes. |

## Local contracts

- **`Tapper.tap()` is the only tap path a flow may use.** `Device.tap_raw()` bypasses the no-tap
  zones and exists solely for the safety layer itself. Do not call it from a flow.
- **`NO_TAP_ZONES` that is enforced lives in `safety.py`.** `config.NO_TAP_ZONES` is an empty
  vestigial list — if you add a zone, add it in `safety.py` or it does nothing.
- **A refused tap raises `UnsafeTap`; it is never downgraded to a warning.** Accidental gem spend is
  the costliest failure this system can produce and no match confidence justifies it.
- **`navigation=True` taps still fire during `--dry-run`**; state-changing taps do not. A dry run
  that cannot get past the disconnect dialog validates nothing.
- **Frame contract is absolute.** A portrait frame means the game is not in front — `_canonicalise`
  raises rather than rotating. Rotating would produce plausible frames of the wrong screen.
- **`battle.in_battle()` stays True under the Tag Team "Pick a Reward!" popup** (a11/a12/a13/a15
  frames): it keys on the End Battle button, which the popup only dims. Detect the popup separately
  (`scratchpad/hud.DimGate`, play-area brightness) before tapping.
- **`DeviceBlocked` vs `DeviceError` is load-bearing.** Blocked = reachable but must not be driven
  (battery, screen, density drift, game not foregrounded); it must never be caught into a retry loop.
- **New capture backends implement `grab() -> Frame` and `close()`, and return native resolution.**
  Templates are cut 1:1; a downscaling source silently breaks every match.
- **`cli.py` holds no game logic.** Shape: parse → lock → connect → assert → delegate to a flow →
  `log.finish()`. Exit codes: `0` ok, `1` error, `2` blocked.
- **The flock is not optional.** Two processes tapping the same village concurrently is exactly the
  situation that produces taps nobody intended.

## Work guidance

- Adding a device capability: put it on `Device` as a thin wrapper over `shell`/`exec-out`, and
  handle the "normal non-zero exit" case explicitly (see `app_pid`, where `pidof` failing means
  "not running", not "broken").
- Timings and payload sizes belong in `TODO.md`'s measured table, not in a new markdown file.
- `report.py` prunes to `SCREENSHOT_RETENTION_RUNS`; the JSONL is append-only and kept forever.
  Anything you want to analyse later must be a field on the `finish()` record, not just a screenshot.

## Verification

- `python3 -m coc.cli status` — proves discovery, battery and screen reads against the live phone.
- Reconnection: `adb disconnect`, then `Device.connect()` (measured 12.2 s).
- Safety changes: assert `is_forbidden()` against each zone's corners *and* verify a real
  `collect --dry-run` still taps the bubbles it should (an over-wide zone loses loot silently).

## Child DOX Index

- [`vision/CLAUDE.md`](vision/CLAUDE.md) — perception layer
- [`flows/CLAUDE.md`](flows/CLAUDE.md) — game flows
