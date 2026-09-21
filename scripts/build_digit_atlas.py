#!/usr/bin/env python3
"""Build the digit atlas from ground-truth-labelled screenshots.

Each sample in assets/digits/labels.json maps a screenshot to the true value of
each HUD counter. Segmentation runs over the known ROIs and the resulting glyph
count must match the label length exactly -- a mismatch means segmentation is
wrong, and silently zipping a short list against a long label would poison the
atlas with mislabelled glyphs, so it is a hard error.

Re-run this after adding samples; it is cheap and idempotent.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from coc import config
from coc.vision.digits import RESOURCE_ROIS, DigitAtlas, segment

SAMPLES = config.DIGITS / "samples"
LABELS = config.DIGITS / "labels.json"


def main() -> int:
    labels = json.loads(LABELS.read_text())
    collected: dict[str, list] = defaultdict(list)
    errors: list[str] = []

    for fname, fields in labels.items():
        img = cv2.imread(str(SAMPLES / fname))
        if img is None:
            errors.append(f"{fname}: unreadable")
            continue
        if (img.shape[1], img.shape[0]) != (config.SCREEN_W, config.SCREEN_H):
            errors.append(f"{fname}: {img.shape[1]}x{img.shape[0]}, expected landscape")
            continue
        for field, truth in fields.items():
            x1, y1, x2, y2 = RESOURCE_ROIS[field]
            glyphs = segment(img[y1:y2, x1:x2])
            if len(glyphs) != len(truth):
                errors.append(
                    f"{fname}/{field}: segmented {len(glyphs)} glyphs but label "
                    f"'{truth}' has {len(truth)} -- refusing to guess the alignment"
                )
                continue
            for g, ch in zip(glyphs, truth):
                collected[ch].append(g.image)

    if errors:
        print("ERRORS:", *errors, sep="\n  ")
        return 1

    atlas = DigitAtlas(dict(collected))
    atlas.save()
    have = sorted(collected)
    missing = [d for d in "0123456789" if d not in collected]
    print(f"atlas written to {config.DIGITS / 'atlas.npz'}")
    print(f"  labels: {''.join(have)}  ({sum(len(v) for v in collected.values())} glyphs)")
    for d in have:
        print(f"    {d}: {len(collected[d])}")
    if missing:
        print(f"  MISSING DIGITS: {''.join(missing)}")
        print("  Reads containing a missing digit will raise UnreadableNumber")
        print("  rather than misread -- add a sample showing one and re-run.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
