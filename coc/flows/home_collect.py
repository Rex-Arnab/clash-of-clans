"""Home Village resource collection.

Collection is written as detect -> tap every bubble -> re-detect, repeated
until the screen is clean or a round makes no progress. That shape is
deliberate: it is correct whether or not tapping one collector sweeps all
collectors of that type (a mechanic the wiki asserts but which I could not
verify), and it measures the answer as a side effect instead of depending on
it. It also self-corrects a missed tap rather than assuming the tap landed.

Progress is judged by bubbles disappearing, not by the resource counters
rising: on a near-maxed account the storages are at capacity, so gold can be
collected successfully while the counter does not move at all.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..capture import ScreencapSource, wait_for_game
from ..device import Device
from ..report import RunLog
from ..safety import Tapper, UnsafeTap
from ..vision.digits import DigitAtlas, read_resources
from ..vision.screens import ensure_village
from ..vision.templates import assert_manifest_matches, find_loot_bubbles

MAX_ROUNDS = 4


@dataclass
class CollectResult:
    rounds: int = 0
    tapped: int = 0
    taps_by_kind: dict[str, int] = field(default_factory=dict)
    bubbles_first_seen: int = 0
    bubbles_remaining: int = 0
    before: dict | None = None
    after: dict | None = None
    refused: list[str] = field(default_factory=list)


def collect_home(device: Device, log: RunLog, dry_run: bool = False) -> CollectResult:
    assert_manifest_matches()
    wait_for_game(device)

    src = ScreencapSource(device)
    tapper = Tapper(device, dry_run=dry_run)
    atlas = DigitAtlas.load()
    result = CollectResult()

    # Establish a known screen before doing anything. The game drops idle
    # sessions, so a scheduled run usually lands on the disconnect dialog.
    frame = ensure_village(device, src, tapper, log)
    log.shot("00_before", frame)
    result.before = read_resources(frame, atlas)
    log.event("before", resources=result.before)

    seen_first = True
    for rnd in range(1, MAX_ROUNDS + 1):
        bubbles = find_loot_bubbles(frame)
        if seen_first:
            result.bubbles_first_seen = len(bubbles)
            seen_first = False
        log.event("detect", round=rnd,
                  bubbles=[{"kind": b.kind, "at": list(b.tap_point),
                            "score": round(b.match.score, 3)} for b in bubbles])
        if not bubbles:
            result.rounds = rnd - 1
            break

        result.rounds = rnd
        for b in bubbles:
            x, y = b.tap_point
            try:
                tapper.tap(x, y, label=f"loot:{b.kind}")
            except UnsafeTap as exc:
                result.refused.append(str(exc))
                log.event("tap_refused", reason=str(exc))
                continue
            result.tapped += 1
            result.taps_by_kind[b.kind] = result.taps_by_kind.get(b.kind, 0) + 1

        if dry_run:
            # Nothing was actually tapped, so the screen cannot change and a
            # second round would report the same bubbles forever.
            break

        frame = src.grab()
        log.shot(f"{rnd:02d}_after_round", frame)
        if len(find_loot_bubbles(frame)) >= len(bubbles):
            log.event("no_progress", round=rnd)
            break

    result.bubbles_remaining = len(find_loot_bubbles(frame))
    result.after = read_resources(frame, atlas)
    log.shot("99_after", frame)
    log.event("after", resources=result.after)
    return result
