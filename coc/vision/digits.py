"""Reading HUD numbers by per-digit template matching.

Tesseract is deliberately not used. The alphabet here is closed (ten digits),
the font is fixed, the density is fixed and the regions are fixed -- which is
the exact case where correlation against a small glyph atlas beats a document
OCR engine, and it avoids a dependency that is not installed.

The resource bars are translucent: the village shows through behind the digits,
so the village itself produces bright speckles inside the ROI. Segmentation
therefore cannot just take every bright blob. Digits are recovered by their
shared baseline and by walking left from the right edge (the numbers are
right-aligned against their icon) until the gap says we have left the number.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np

from .. import config

# Native-resolution ROIs, landscape. Generous on the left; the walk-from-right
# logic below is what actually bounds the number.
RESOURCE_ROIS: dict[str, tuple[int, int, int, int]] = {
    "gold": (1980, 42, 2205, 80),
    "elixir": (1980, 142, 2205, 180),
    "dark": (1980, 242, 2205, 280),
    "gems": (2090, 342, 2205, 378),
}

GLYPH_BOX = (20, 28)          # atlas cell (w, h) every glyph is resized into
MIN_H, MAX_H = 19, 28         # a digit's height in native pixels
MIN_W, MAX_W = 5, 26          # real digits measure 16-21px wide
MIN_AREA = 45
BASELINE_TOL = 3              # px; digits share a baseline, strays rarely do
MAX_INTRA_GAP = 25            # px; measured: separators reach 13px, the
                              # nearest stray sat 30px out


class UnreadableNumber(ValueError):
    """The region did not yield a confident reading.

    Raised rather than returning a best guess: a silently misread digit
    corrupts a loot threshold or a before/after delta, and a retry is cheap.
    """


@dataclass(frozen=True)
class Glyph:
    x: int
    y: int
    w: int
    h: int
    image: np.ndarray        # binary mask crop, GLYPH_BOX sized


def _mask(bgr: np.ndarray) -> np.ndarray:
    """Isolate the near-white glyph bodies. Low saturation, high value."""
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    return cv2.inRange(hsv, (0, 0, 185), (180, 70, 255))


def segment(bgr: np.ndarray) -> list[Glyph]:
    """Return the number's glyphs, left to right."""
    m = _mask(bgr)
    count, _, stats, _ = cv2.connectedComponentsWithStats(m, 8)

    cands = []
    for i in range(1, count):
        x, y, w, h, area = stats[i]
        if MIN_H <= h <= MAX_H and MIN_W <= w <= MAX_W and area >= MIN_AREA:
            cands.append((x, y, w, h))
    if not cands:
        return []

    # Digits sit on a common baseline; a stray highlight from the village
    # behind the translucent bar almost never shares it.
    baseline = Counter(y + h for _, y, _, h in cands).most_common(1)[0][0]
    cands = [c for c in cands if abs((c[1] + c[3]) - baseline) <= BASELINE_TOL]
    if not cands:
        return []

    # Numbers are right-aligned against their icon, so the rightmost glyph is
    # always real. Walk left while the spacing still looks like one number.
    cands.sort(key=lambda c: c[0])
    kept = [cands[-1]]
    for c in reversed(cands[:-1]):
        prev = kept[-1]
        if prev[0] - (c[0] + c[2]) <= MAX_INTRA_GAP:
            kept.append(c)
        else:
            break
    kept.reverse()

    out = []
    for x, y, w, h in kept:
        out.append(Glyph(x, y, w, h, _fit_cell(m[y:y + h, x:x + w])))
    return out


def _fit_cell(binary: np.ndarray) -> np.ndarray:
    """Scale a glyph into the atlas cell WITHOUT distorting its aspect ratio.

    Stretching every glyph to fill the cell squashes a narrow "1" (9px wide)
    by 2.2x horizontally while leaving an "8" (19px) almost untouched, so tiny
    rendering differences in the stretched glyph cost a lot of correlation --
    measured: a correct "1" scored 0.750 and fell under the confidence gate.
    Scaling to fit and centring on a blank cell keeps "1" narrow and stable.
    """
    bw, bh = GLYPH_BOX
    h, w = binary.shape[:2]
    scale = min(bw / w, bh / h)
    nw, nh = max(1, int(round(w * scale))), max(1, int(round(h * scale)))
    resized = cv2.resize(binary, (nw, nh), interpolation=cv2.INTER_AREA)
    cell = np.zeros((bh, bw), np.uint8)
    ox, oy = (bw - nw) // 2, (bh - nh) // 2
    cell[oy:oy + nh, ox:ox + nw] = resized
    return cell


class DigitAtlas:
    """Labelled glyph templates, persisted as a single npz plus a manifest."""

    def __init__(self, templates: dict[str, list[np.ndarray]]) -> None:
        self.templates = templates

    @classmethod
    def load(cls, path: Path | None = None) -> "DigitAtlas":
        path = path or (config.DIGITS / "atlas.npz")
        if not path.exists():
            raise FileNotFoundError(
                f"no digit atlas at {path}; run scripts/build_digit_atlas.py"
            )
        data = np.load(path)
        tpl: dict[str, list[np.ndarray]] = {}
        for key in data.files:
            label = key.split("_", 1)[0]
            tpl.setdefault(label, []).append(data[key])
        return cls(tpl)

    def save(self, path: Path | None = None) -> None:
        path = path or (config.DIGITS / "atlas.npz")
        path.parent.mkdir(parents=True, exist_ok=True)
        flat = {}
        for label, imgs in self.templates.items():
            for i, img in enumerate(imgs):
                flat[f"{label}_{i}"] = img
        np.savez_compressed(path, **flat)
        (path.parent / "atlas.json").write_text(
            json.dumps(
                {
                    "labels": sorted(self.templates),
                    "counts": {k: len(v) for k, v in sorted(self.templates.items())},
                    "glyph_box": list(GLYPH_BOX),
                    "screen": [config.SCREEN_W, config.SCREEN_H],
                    "density": config.EXPECTED_DENSITY,
                },
                indent=2,
            )
        )

    def classify(self, cell: np.ndarray) -> tuple[str, float, float]:
        """Return (label, best_score, runner_up_score)."""
        scores: list[tuple[float, str]] = []
        a = cell.astype(np.float32)
        for label, imgs in self.templates.items():
            best = max(
                float(cv2.matchTemplate(a, t.astype(np.float32),
                                        cv2.TM_CCOEFF_NORMED)[0, 0])
                for t in imgs
            )
            scores.append((best, label))
        scores.sort(reverse=True)
        runner = scores[1][0] if len(scores) > 1 else 0.0
        return scores[0][1], scores[0][0], runner


@lru_cache(maxsize=1)
def default_atlas() -> DigitAtlas:
    """The process-wide atlas, for callers that have no atlas to hand.

    Loading is disk I/O and every caller wants the same file; templates._load
    caches for the same reason. Callers that already hold an atlas should keep
    passing it explicitly -- this exists so screen classification does not need
    an atlas threaded through its signature.
    """
    return DigitAtlas.load()


def read_number(frame: np.ndarray, roi: tuple[int, int, int, int],
                atlas: DigitAtlas) -> int:
    """Read one right-aligned integer out of a fixed region."""
    x1, y1, x2, y2 = roi
    glyphs = segment(frame[y1:y2, x1:x2])
    if not glyphs:
        raise UnreadableNumber(f"no glyphs in roi {roi}")

    digits = []
    for g in glyphs:
        label, best, runner = atlas.classify(g.image)
        # An ambiguous glyph is reported, never guessed: a misread digit is a
        # wrong loot delta that looks entirely plausible in the log.
        if best < config.DIGIT_THRESHOLD or (best - runner) < 0.05:
            raise UnreadableNumber(
                f"ambiguous glyph at x={g.x} in roi {roi}: "
                f"{label} {best:.3f} vs runner-up {runner:.3f}"
            )
        digits.append(label)
    return int("".join(digits))


def read_resources(frame: np.ndarray, atlas: DigitAtlas) -> dict[str, int | None]:
    """Read all four HUD counters. Unreadable fields come back as None."""
    out: dict[str, int | None] = {}
    for name, roi in RESOURCE_ROIS.items():
        try:
            out[name] = read_number(frame, roi, atlas)
        except UnreadableNumber:
            out[name] = None
    return out
