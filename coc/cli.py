"""Command-line entry point. This is what the scheduler invokes."""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import json
import random
import sys
import time

from . import config
from .capture import assert_geometry
from .device import Device, DeviceBlocked, DeviceError
from .flows.home_collect import collect_home
from .report import RunLog


@contextlib.contextmanager
def _single_run():
    """Refuse to start if another run is still going.

    A collect run takes 20-30s but a reload adds ~18s and a slow link can push
    it further, so an overrunning run could still be tapping when the scheduler
    fires the next one. Two processes tapping the same village independently is
    exactly the situation that produces taps nobody intended.
    """
    config.RUNS.mkdir(parents=True, exist_ok=True)
    lock = config.RUNS / ".run.lock"
    fh = lock.open("w")
    try:
        fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        fh.close()
        raise SystemExit("another run is already in progress; skipping")
    try:
        yield
    finally:
        fcntl.flock(fh, fcntl.LOCK_UN)
        fh.close()


def _delta(before: dict | None, after: dict | None, key: str):
    if not before or not after:
        return None
    b, a = before.get(key), after.get(key)
    return (a - b) if isinstance(a, int) and isinstance(b, int) else None


def cmd_collect(args: argparse.Namespace) -> int:
    # A scheduled run starts with a random short delay so the session does not
    # begin at exactly :00 every hour.
    if args.jitter:
        time.sleep(random.uniform(0, args.jitter))
    with _single_run():
        return _collect_locked(args)


def _collect_locked(args: argparse.Namespace) -> int:

    log = RunLog("home_collect", dry_run=args.dry_run)
    try:
        device = Device.connect()
        assert_geometry(device)
        device.require_ready()
        result = collect_home(device, log, dry_run=args.dry_run)
    except DeviceBlocked as exc:
        # Expected and recoverable: low battery, screen off, game not reachable.
        # Reported as blocked rather than failed, and explicitly not retried.
        rec = log.finish("blocked", reason=str(exc))
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2
    except (DeviceError, Exception) as exc:  # noqa: BLE001 - logged and surfaced
        log.finish("error", error=f"{type(exc).__name__}: {exc}")
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    rec = log.finish(
        "ok",
        rounds=result.rounds,
        bubbles_first_seen=result.bubbles_first_seen,
        tapped=result.tapped,
        taps_by_kind=result.taps_by_kind,
        bubbles_remaining=result.bubbles_remaining,
        refused=result.refused,
        before=result.before,
        after=result.after,
        gained={k: _delta(result.before, result.after, k)
                for k in ("gold", "elixir", "dark")},
    )
    if args.json:
        print(json.dumps(rec["gained"]))
    else:
        g = rec["gained"]
        print(f"collected {result.tapped} bubbles in {result.rounds} round(s); "
              f"gold +{g['gold']} elixir +{g['elixir']} dark +{g['dark']} "
              f"({rec['duration_s']}s)")
    return 0


def cmd_status(_: argparse.Namespace) -> int:
    try:
        d = Device.connect()
    except DeviceError as exc:
        print(f"device: UNREACHABLE ({exc})")
        return 1
    level, charging = d.battery()
    print(f"device   : {d.addr}")
    print(f"battery  : {level}% {'charging' if charging else 'discharging'}")
    print(f"screen   : {'on' if d.screen_on() else 'off'}")
    print(f"game pid : {d.app_pid()}")
    return 0


def cmd_summary(args: argparse.Namespace) -> int:
    """Roll up recent runs -- what the daily report reads."""
    if not config.RUN_LOG.exists():
        print("no runs recorded yet")
        return 0
    rows = [json.loads(l) for l in config.RUN_LOG.read_text().splitlines() if l.strip()]
    rows = rows[-args.limit:]
    tot = {"gold": 0, "elixir": 0, "dark": 0}
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
        for k in tot:
            v = (r.get("gained") or {}).get(k)
            if isinstance(v, int):
                tot[k] += v
    print(f"runs: {len(rows)}  " + "  ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    print(f"collected: gold +{tot['gold']:,}  elixir +{tot['elixir']:,}  dark +{tot['dark']:,}")
    return 0


def cmd_locate(args: argparse.Namespace) -> int:
    """Locate defensive buildings in a frame (file, or a live grab)."""
    import cv2

    from .vision import locate
    from .vision.vlm import VLMError
    from .vision.yolo import YoloError

    if args.image:
        frame = cv2.imread(args.image)
        if frame is None:
            print(f"cannot read {args.image}", file=sys.stderr)
            return 1
    else:
        # A live grab inherits the capture contract: a portrait frame means the game
        # is not in front, which is BLOCKED (exit 2), not an error. Surfaced the same
        # way collect does -- a traceback here would read as a code fault.
        from .capture import CaptureError, ScreencapSource
        try:
            src = ScreencapSource(Device.connect())
        except DeviceBlocked as exc:
            print(f"BLOCKED: {exc}", file=sys.stderr)
            return 2
        except DeviceError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        try:
            frame = src.grab()
        except CaptureError as exc:
            print(f"BLOCKED: {exc}", file=sys.stderr)
            return 2
        finally:
            src.close()

    classes = tuple(args.classes.split(",")) if args.classes else locate.DEFAULT_CLASSES
    t0 = time.time()
    try:
        dets = locate.locate_buildings(frame, classes, verify=not args.no_verify,
                                       detector=args.detector)
    except (VLMError, YoloError, ValueError) as exc:
        print(f"locate failed: {exc}")
        return 1

    if args.json:
        print(json.dumps([d.as_dict() for d in dets], indent=2))
    else:
        counts: dict[str, int] = {}
        for d in dets:
            counts[d.label] = counts.get(d.label, 0) + 1
        print(f"{len(dets)} buildings in {time.time() - t0:.1f}s  "
              + "  ".join(f"{k}={v}" for k, v in sorted(counts.items())))
        for d in sorted(dets, key=lambda x: (x.label, x.x1)):
            mark = "" if d.verified else "  (unverified)"
            print(f"  {d.label:<14} centre={d.centre}  conf={d.confidence:.2f}  "
                  f"{d.source}{mark}")
    if args.overlay:
        cv2.imwrite(args.overlay, locate.draw(frame, dets))
        print(f"overlay -> {args.overlay}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="coc", description="Clash of Clans automation")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("collect", help="collect Home Village resources")
    c.add_argument("--dry-run", action="store_true",
                   help="perceive and decide, but send no collection taps")
    c.add_argument("--jitter", type=float, default=0.0,
                   help="sleep up to N seconds before starting")
    c.add_argument("--json", action="store_true")
    c.set_defaults(func=cmd_collect)

    s = sub.add_parser("status", help="device and game state")
    s.set_defaults(func=cmd_status)

    m = sub.add_parser("summary", help="roll up recent runs")
    m.add_argument("--limit", type=int, default=24)
    m.set_defaults(func=cmd_summary)

    lo = sub.add_parser("locate",
                        help="locate defensive buildings in a frame (local YOLO + VLM)")
    lo.add_argument("--image", help="frame to read; omit to grab from the device")
    lo.add_argument("--classes", help="comma-separated subset of the known classes")
    lo.add_argument("--detector", choices=("hybrid", "vlm"), default="hybrid",
                    help="hybrid: air_defense/x_bow/inferno_tower from the local model "
                         "(default); vlm: every class through the staged VLM pipeline")
    lo.add_argument("--no-verify", action="store_true",
                    help="skip the per-crop VLM verify. hybrid: local boxes >= 0.80 "
                         "only (98.7%% precise, lower recall, no API call); "
                         "vlm: 86%% precision, ~3x cheaper")
    lo.add_argument("--overlay", help="write a boxed PNG here for grading")
    lo.add_argument("--json", action="store_true")
    lo.set_defaults(func=cmd_locate)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
