"""Masked template matching, and loot-bubble detection built on top of it.

Two things make matching here non-obvious, and both are handled below.

First, the world animates: water, clouds, troop idle loops and the bubbles'
own bob. Templates are therefore matched with an alpha mask so that only the
element's own pixels contribute and the varying background behind it does not.
An unmasked rectangular crop of a loot bubble scores 0.75 on an identical
bubble sitting on different scenery, which is indistinguishable from noise.

Second, all three resource bubbles share one frame and differ only in the icon
inside. Masking out the interior therefore detects gold, elixir and dark
elixir with a single template, and the interior hue classifies which it is.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np

from .. import config

# Screen regions that are HUD chrome rather than village. Bubbles found inside
# these are false positives (the gem and league icons match the frame shape).
HUD_ZONES: list[tuple[int, int, int, int]] = [
    (85, 0, 480, 95),         # top left: level badge and name
    (95, 95, 232, 900),       # left rail: social, attack log, boosts
    (700, 0, 1720, 95),       # top centre: builders, shield timer
    (1950, 0, 2392, 425),     # right: resource bars and gems
    (2170, 595, 2300, 848),   # right edge: layout / settings buttons. Measured
                              # (2186,611)-(2284,708) and (2186,734)-(2284,832).
                              # The previous (2270,425,2392,830) was ~85px too
                              # far right and covered a 14px sliver of each.
    (60, 845, 650, 1080),     # bottom left: Attack, boost, calendar
    (2040, 830, 2392, 1080),  # bottom right: Shop
    (1955, 940, 2072, 1057),  # bottom right: base-layout / notes button, which
                              # sits left of the Shop zone. Measured
                              # (1965,950)-(2062,1047). Kept as its own tight box
                              # rather than widening Shop, which would have swept
                              # in ~85x120px of village above it.
]
# Deliberately tight. An earlier version used a full-height left rail of 300px
# and silently swallowed a real dark-elixir bubble sitting just inside the
# village edge -- an over-wide exclusion zone loses loot without any error.


@dataclass(frozen=True)
class Match:
    x: int
    y: int
    w: int
    h: int
    score: float

    @property
    def centre(self) -> tuple[int, int]:
        return self.x + self.w // 2, self.y + self.h // 2


@dataclass(frozen=True)
class Bubble:
    match: Match
    kind: str          # "gold" | "elixir" | "dark" | "unknown"

    @property
    def tap_point(self) -> tuple[int, int]:
        """Where to tap. The frame's centre sits on the icon, which is the
        reliably hittable part; the pointer below it overlaps the building."""
        x, y = self.match.centre
        return x, y - 6


@lru_cache(maxsize=None)
def _load(name: str) -> tuple[np.ndarray, np.ndarray | None]:
    tpl = cv2.imread(str(config.TEMPLATES / f"{name}.png"))
    if tpl is None:
        raise FileNotFoundError(f"missing template {name}.png")
    mpath = config.TEMPLATES / f"{name}_mask.png"
    mask = cv2.imread(str(mpath), cv2.IMREAD_GRAYSCALE) if mpath.exists() else None
    return tpl, mask


def manifest() -> dict:
    return json.loads((config.TEMPLATES / "manifest.json").read_text())


def assert_manifest_matches() -> None:
    """Refuse to run against a device the templates were not cut for.

    Resolution or density drift shifts every match by a scale factor and the
    failure is silent -- taps land plausibly but wrongly -- so it is checked.
    """
    m = manifest()
    if tuple(m["screen"]) != (config.SCREEN_W, config.SCREEN_H):
        raise RuntimeError(
            f"templates cut for {m['screen']}, running at "
            f"{[config.SCREEN_W, config.SCREEN_H]}"
        )
    if m["density"] != config.EXPECTED_DENSITY:
        raise RuntimeError(
            f"templates cut at density {m['density']}, expected "
            f"{config.EXPECTED_DENSITY}"
        )


def in_hud(x: int, y: int) -> bool:
    return any(x1 <= x <= x2 and y1 <= y <= y2 for x1, y1, x2, y2 in HUD_ZONES)


def find_all(frame: np.ndarray, name: str, threshold: float,
             min_separation: int = 45) -> list[Match]:
    """All non-overlapping matches, best first.

    Uses TM_SQDIFF_NORMED (lower is better) because with a mask it gave the
    cleanest separation on real frames: 0.00/0.09/0.11 for true bubbles
    against 0.196 for the first false positive.
    """
    tpl, mask = _load(name)
    h, w = tpl.shape[:2]
    res = cv2.matchTemplate(frame, tpl, cv2.TM_SQDIFF_NORMED, mask=mask)
    res = np.nan_to_num(res, nan=1e9, posinf=1e9, neginf=1e9)

    ys, xs = np.where(res <= threshold)
    ordered = sorted(zip(res[ys, xs], xs, ys))
    kept: list[Match] = []
    for score, x, y in ordered:
        if all(abs(int(x) - m.x) > min_separation or abs(int(y) - m.y) > min_separation
               for m in kept):
            kept.append(Match(int(x), int(y), w, h, float(score)))
    return kept


# Interior hue ranges, sampled from the icon inside the bubble frame.
_KIND_RANGES = {
    "gold": ((18, 120, 150), (34, 255, 255)),
    "elixir": ((138, 90, 140), (170, 255, 255)),
    "dark": ((0, 0, 0), (180, 255, 95)),
}


def classify_bubble(frame: np.ndarray, m: Match) -> str:
    """Name the resource by the dominant hue of the bubble's interior."""
    cx, cy = m.centre
    patch = frame[max(0, cy - 16):cy + 16, max(0, cx - 16):cx + 16]
    if patch.size == 0:
        return "unknown"
    hsv = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV)
    best, best_frac = "unknown", 0.0
    for kind, (lo, hi) in _KIND_RANGES.items():
        frac = float(cv2.inRange(hsv, lo, hi).mean()) / 255.0
        if frac > best_frac:
            best, best_frac = kind, frac
    return best if best_frac >= 0.15 else "unknown"


def find_loot_bubbles(frame: np.ndarray, threshold: float = 0.15) -> list[Bubble]:
    """Every collectable loot bubble currently on screen, HUD excluded."""
    out = []
    for m in find_all(frame, "loot_bubble", threshold):
        cx, cy = m.centre
        if in_hud(cx, cy):
            continue
        out.append(Bubble(m, classify_bubble(frame, m)))
    return out
