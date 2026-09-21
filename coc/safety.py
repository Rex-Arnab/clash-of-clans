"""Interlocks that sit below the flow layer and cannot be bypassed by it.

The flows decide *what* to tap; this module decides what is allowed to be
tapped at all. Keeping the refusal here rather than in each flow means a new
flow cannot forget it, and a confident-but-wrong match cannot spend money.
"""

from __future__ import annotations

import random

from . import config
from .device import Device

# Regions where a tap can cost real money or irreversibly spend resources.
# A tap resolving inside one of these is refused outright, whatever the matcher
# believes it found -- an accidental gem purchase is the costliest failure this
# system can produce, and no detection confidence justifies risking it.
# Bounds are MEASURED off a live frame, not estimated -- see the scout pass of
# 2026-09-08. Each zone is the element's own box plus a small margin; they are
# kept tight because a zone that overhangs village refuses real loot.
NO_TAP_ZONES: list[tuple[int, int, int, int]] = [
    (2040, 830, 2392, 1080),   # Shop button
    (1950, 300, 2392, 430),    # gem counter and the green "+" buy button
    (1495, 5, 1620, 100),      # shield timer's green "+": opens a gem purchase.
                               # Measured (1515,25)-(1606,100). Sits inside the
                               # top-centre HUD zone, so the margin costs no loot.
    (2150, 425, 2392, 520),    # "Upgrade" suggestion button. NOTE: only rendered
                               # when a builder is free; with 0/7 builders this
                               # zone lies over open village and will refuse a
                               # bubble there (logged in `refused`, not silent).
    (325, 862, 488, 1062),     # season/boost button ("2x" badge over a shield
                               # with a 22d timer). Measured (331,870)-(479,1054).
                               # Unidentified panel -- protected until it is known.
    (60, 845, 340, 1080),      # Attack button (attacks are a separate flow)
]


class UnsafeTap(RuntimeError):
    """A tap was refused because it landed in a protected region."""


def is_forbidden(x: int, y: int) -> bool:
    return any(x1 <= x <= x2 and y1 <= y <= y2 for x1, y1, x2, y2 in NO_TAP_ZONES)


class Tapper:
    """Human-ish tapping with the no-tap zones enforced.

    `dry_run` runs every decision and records the taps without sending them,
    which is how a flow is validated against the live game before it is
    allowed to touch it.
    """

    def __init__(self, device: Device, dry_run: bool = False) -> None:
        self.device = device
        self.dry_run = dry_run
        self.taps: list[tuple[int, int, str]] = []

    def tap(self, x: int, y: int, label: str = "", jitter: bool = True,
            navigation: bool = False) -> None:
        """Tap, subject to the no-tap zones.

        `navigation=True` marks a move that only changes which screen we are
        looking at -- dismissing a dialog, reloading the game. Those still
        execute during a dry run, because a dry run that cannot get past the
        disconnect dialog would validate nothing. Collection and attack taps,
        which change game state, stay simulated.
        """
        if jitter:
            r = config.TAP_JITTER_FRAC * 12
            x += int(random.gauss(0, r))
            y += int(random.gauss(0, r))
        x = max(0, min(config.SCREEN_W - 1, x))
        y = max(0, min(config.SCREEN_H - 1, y))

        if is_forbidden(x, y):
            raise UnsafeTap(f"refused tap at ({x},{y}) for {label!r}: protected region")

        self.taps.append((x, y, label))
        if not self.dry_run or navigation:
            self.device.tap_raw(x, y)
            self.device.human_pause()
