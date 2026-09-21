"""Staged building localisation: boundary -> tiles -> detect -> merge -> verify.

Asking the VLM to find every building in one whole-frame call produces confident,
WRONG boxes. Measured 2026-09-12 on 5 unseen battle-scout frames: it returned exactly
4 air defenses on every base -- the correct number for these town halls -- while only
13 of those 20 boxes sat on an actual Air Defense. One was a gold storage with a
"2d 9H" timer, one an orange lava cauldron, one a spell building. The count looked
perfect because the model was filling a quota from prior knowledge of the game rather
than reading pixels, which is the most expensive kind of wrong here: it is invisible
in any metric that counts detections.

Splitting the question into stages fixes it, because each stage is asked something it
can actually see at the resolution it is given:

    stage       question asked of the VLM                          measured (n=5 bases)
    ----------- -------------------------------------------------- --------------------
    1 boundary  where is the base, where is the HUD                 reliable
    2 tiles     detect within ONE 3x2 overlapping native-res crop,  precision 86%
                upscaled 1.6x                                       recall    90%
    3 merge     NMS across tile overlaps (no model call)            --
    4 verify    name the ONE building in this close-up crop         precision 100%
                                                                    recall    90%

Stage 4 is what removes the residual errors: at native zoom an X-Bow (tan base, dark
horizontal crossbow limbs) is unmistakable against an Air Defense (purple platform,
vertical gold-banded tubes with red conical tips), and the same model that confused
them at 1450 px wide separates them perfectly on a 360 px crop of one building.

Per the root contract every coordinate here is native landscape 2392x1080: tile
offsets are added back before any Detection leaves this module, so callers never see
a normalised or tile-local number.

Cost/latency per frame (7 + N calls, threaded): ~$0.010, ~15 s -- inside the 54 s
battle prep window. Reproduce with:

    python3 -m coc.cli locate --image <frame.png> --overlay /tmp/boxes.png

Stage 0 (default, `detector="hybrid"`): the classes in `FAST_CLASSES` skip all of the
above and come from the local YOLO detector in `yolo.py` (~84 ms, no API call). Boxes at
`yolo.ACCEPT_CONF` or above are returned as-is; boxes in the review band only survive a
stage-4 crop verify. Only the classes the detector was never graded on (`town_hall`,
`loot_bubble`) still pay for stages 1-4. `detector="vlm"` is the old path, kept for A/B.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import cv2
import numpy as np

from . import vlm, yolo
from .vlm import VLMError

# What each class looks like. These marks are load-bearing: naming the confusable
# pair explicitly (air_defense vs x_bow) is most of what stage 4 buys.
CLASS_MARKS: dict[str, str] = {
    "air_defense": "PURPLE/dark platform, several near-VERTICAL gold-banded tubes "
                   "each tipped with a RED or BLACK CONE",
    "x_bow": "TAN/GOLD base, dark HORIZONTAL crossbow limbs and a bowstring, "
             "often a yellow ammo drum",
    "inferno_tower": "tall tower with a glowing ORANGE/RED flame or lava at the top",
    "town_hall": "the single largest, most ornate central building",
    "loot_bubble": "large translucent MAGENTA/PINK dome collectible",
}
DEFAULT_CLASSES = tuple(CLASS_MARKS)
# Answered by `yolo.py` in hybrid mode. Only classes graded there may appear here.
FAST_CLASSES = frozenset(yolo.EXPOSED.values())
DETECTORS = ("hybrid", "vlm")

# Stage 4 may relabel a detection into any of these. The extras exist so a wrong box
# has somewhere truthful to go -- without them the verifier is forced to pick one of
# the requested classes and simply confirms the error.
VERIFY_CLASSES = tuple(CLASS_MARKS) + (
    "wizard_tower", "cannon", "archer_tower", "mortar", "scattershot",
    "eagle_artillery", "air_sweeper", "storage", "clan_castle", "army_camp",
    "builder_hut", "decoration", "other",
)

# 3x2 with 18% overlap: measured to keep every building whole in at least one tile at
# this zoom level. Upscaling 1.6x is what makes a ~90 px building legible to the model.
COLS, ROWS, OVERLAP, UPSCALE = 3, 2, 0.18, 1.6
# Stage 1 intermittently omits `base_bounds` (seen once live 2026-09-12), so the last
# attempt switches model rather than re-rolling the same one. Measured over 12 calls
# each on 3 real frames: `gemini-3-flash-preview` 9/9, `gemini-3.1-flash-lite` 9/9,
# `gemini-3.5-flash` 0/9 (answers with prose reasoning, not JSON), `gemini-3.8-flash`
# 0/9 (markdown-fenced and truncated at max_tokens). The fallback is a flash, not a
# pro: pro was reliable too but ~8x the input price for a task flash-lite does 9/9.
BOUNDS_ATTEMPTS = 3
BOUNDS_FALLBACK_MODEL = "google/gemini-3.1-flash-lite"
IOU_SAME, IOU_CROSS = 0.30, 0.45
MIN_CONFIDENCE = 0.5
VERIFY_CROP_H = 360   # px tall; below ~250 the confusable pair stops separating
VERIFY_PAD = 20       # px of context around a box, so walls/neighbours are visible


@dataclass(frozen=True)
class Detection:
    """One building, in native 2392x1080 pixels."""

    label: str
    confidence: float
    x1: int
    y1: int
    x2: int
    y2: int
    verified: bool = False
    source: str = "vlm"   # "yolo" (stage 0) or "vlm" (stages 1-4)

    @property
    def centre(self) -> tuple[int, int]:
        return (self.x1 + self.x2) // 2, (self.y1 + self.y2) // 2

    def as_dict(self) -> dict:
        return {"label": self.label, "confidence": round(self.confidence, 3),
                "box": [self.x1, self.y1, self.x2, self.y2],
                "centre": list(self.centre), "verified": self.verified,
                "source": self.source}


def _class_block(classes) -> str:
    return "\n".join(f'- "{c}"  {CLASS_MARKS[c]}' for c in classes if c in CLASS_MARKS)


BOUNDS_PROMPT = (
    "Clash of Clans screenshot. Return the LAYOUT REGIONS, not buildings.\n"
    'Labels: "base_bounds" (tight box around the whole walled village, excluding the '
    'empty grass border and excluding all UI overlays), "hud_top", "hud_right", '
    '"hud_left", "hud_bottom".\n'
    'ONLY a JSON array: [{"label":"<region>","box_2d":[ymin,xmin,ymax,xmax]}] '
    "normalised 0-1000, order [ymin,xmin,ymax,xmax], 0,0 = top-left."
)


def _norm_to_px(box, x0: float, y0: float, w: float, h: float) -> tuple[int, int, int, int]:
    """A model box normalised 0-1000 within some region -> native pixels."""
    ymin, xmin, ymax, xmax = (float(v) for v in box[:4])
    return (int(x0 + xmin / 1000 * w), int(y0 + ymin / 1000 * h),
            int(x0 + xmax / 1000 * w), int(y0 + ymax / 1000 * h))


def _bounds_once(frame: np.ndarray, model: str | None) -> tuple[int, int, int, int]:
    h, w = frame.shape[:2]
    for region in vlm.ask_list(frame, BOUNDS_PROMPT, max_tokens=600, model=model):
        if not isinstance(region, dict):
            continue
        if region.get("label") == "base_bounds" and isinstance(region.get("box_2d"), list):
            x1, y1, x2, y2 = _norm_to_px(region["box_2d"], 0, 0, w, h)
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)
            if x2 - x1 < w * 0.25 or y2 - y1 < h * 0.25:
                raise VLMError(f"implausible base_bounds {(x1, y1, x2, y2)} on {w}x{h}")
            return x1, y1, x2, y2
    raise VLMError("no base_bounds region in response")


def base_bounds(frame: np.ndarray, *, attempts: int = BOUNDS_ATTEMPTS) -> tuple[int, int, int, int]:
    """Stage 1: the walled village as native px (x1, y1, x2, y2).

    Retries, then switches model. This stage is the one flaky part of the pipeline: the
    default model answers the 5-region layout question correctly 9/9 in a measured burst
    but intermittently omits `base_bounds` entirely (seen live once on 2026-09-12). A
    missing or wrong crop silently truncates every later stage, so we retry and switch
    rather than fall back to the full frame -- and still raise if every attempt fails,
    per the repo's fail-closed contract.
    """
    last: VLMError | None = None
    for i in range(max(1, attempts)):
        # Last attempt escalates to the stronger model rather than rolling the dice again.
        model = BOUNDS_FALLBACK_MODEL if i == attempts - 1 and attempts > 1 else None
        try:
            return _bounds_once(frame, model)
        except VLMError as exc:
            last = exc
    raise VLMError(f"base_bounds failed after {attempts} attempts: {last}")


def _tiles(bounds: tuple[int, int, int, int], shape) -> list[tuple[int, int, int, int]]:
    h, w = shape[:2]
    x0, y0, x1, y1 = bounds
    tw = (x1 - x0) / (COLS - (COLS - 1) * OVERLAP)
    th = (y1 - y0) / (ROWS - (ROWS - 1) * OVERLAP)
    out = []
    for r in range(ROWS):
        for c in range(COLS):
            x = int(x0 + c * tw * (1 - OVERLAP))
            y = int(y0 + r * th * (1 - OVERLAP))
            out.append((x, y, int(min(tw, w - x)), int(min(th, h - y))))
    return out


def _detect_tile(frame: np.ndarray, tile, classes) -> list[Detection]:
    x, y, w, h = tile
    crop = frame[y:y + h, x:x + w]
    crop = cv2.resize(crop, (int(w * UPSCALE), int(h * UPSCALE)))
    prompt = (
        "CROP of a Clash of Clans village. Detect ONLY these, and only if FULLY OR "
        "MOSTLY visible in this crop:\n" + _class_block(classes) + "\n"
        'ONLY a JSON array: [{"label":"<class>","box_2d":[ymin,xmin,ymax,xmax],'
        '"confidence":0.0-1.0}] normalised 0-1000 relative to THIS CROP. '
        "Omit absent classes; return [] if none are present. Do not guess."
    )
    try:
        raw = vlm.ask_list(crop, prompt, max_w=crop.shape[1])
    except VLMError:
        return []   # one blind tile must not fail the whole frame
    out = []
    for d in raw:
        box = d.get("box_2d")
        if not isinstance(box, list) or len(box) < 4 or d.get("label") not in classes:
            continue
        px = _norm_to_px(box, x, y, w, h)
        out.append(Detection(str(d["label"]), float(d.get("confidence", 0.5)), *px))
    return out


def _iou(a: Detection, b: Detection) -> float:
    ix = max(0, min(a.x2, b.x2) - max(a.x1, b.x1))
    iy = max(0, min(a.y2, b.y2) - max(a.y1, b.y1))
    inter = ix * iy
    union = (a.x2 - a.x1) * (a.y2 - a.y1) + (b.x2 - b.x1) * (b.y2 - b.y1) - inter
    return inter / union if union > 0 else 0.0


def _nms(dets: list[Detection]) -> list[Detection]:
    """Stage 3. Cross-class threshold is looser than same-class: two tiles that saw the
    same building and disagreed on its NAME must still collapse to one box."""
    kept: list[Detection] = []
    for d in sorted((x for x in dets if x.confidence >= MIN_CONFIDENCE),
                    key=lambda x: -x.confidence):
        if not any(_iou(k, d) > (IOU_SAME if k.label == d.label else IOU_CROSS)
                   for k in kept):
            kept.append(d)
    return kept


VERIFY_PROMPT = (
    "This is a close-up crop of ONE building from Clash of Clans. Name the building "
    "at the CENTRE of the crop.\n\nDistinguishing marks:\n"
    + "\n".join(f'- "{c}"  {CLASS_MARKS[c]}' for c in CLASS_MARKS)
    + "\nOther allowed labels: "
    + ", ".join(f'"{c}"' for c in VERIFY_CLASSES if c not in CLASS_MARKS)
    + '\n\nReply ONLY: [{"label":"<one label>","confidence":0.0-1.0}]'
)


def _verify(frame: np.ndarray, d: Detection) -> Detection | None:
    """Stage 4: re-read one detection from its own crop. Returns the corrected
    Detection, or None when the crop is not one of the requested classes."""
    h, w = frame.shape[:2]
    x1, y1 = max(0, d.x1 - VERIFY_PAD), max(0, d.y1 - VERIFY_PAD)
    x2, y2 = min(w, d.x2 + VERIFY_PAD), min(h, d.y2 + VERIFY_PAD)
    crop = frame[y1:y2, x1:x2]
    if crop.size == 0:
        return None
    scale = VERIFY_CROP_H / crop.shape[0]
    crop = cv2.resize(crop, (int(crop.shape[1] * scale), VERIFY_CROP_H))
    try:
        raw = vlm.ask_list(crop, VERIFY_PROMPT, max_tokens=300, max_w=crop.shape[1])
    except VLMError:
        return d   # verifier unreachable: keep stage-2's answer, flagged unverified
    if not raw or not isinstance(raw[0], dict):
        return d
    label = str(raw[0].get("label", ""))
    if label not in CLASS_MARKS:
        return None
    return Detection(label, float(raw[0].get("confidence", d.confidence)),
                     d.x1, d.y1, d.x2, d.y2, verified=True)


def _locate_fast(frame: np.ndarray, classes: set[str], *, verify: bool,
                 workers: int) -> list[Detection]:
    """Stage 0: the local detector, plus a crop verify for its uncertain band.

    Below `yolo.ACCEPT_CONF` two thirds of the graded boxes were banners, hero cards
    and countdown text, so a review-band box is returned ONLY if the VLM gives it the
    SAME name on its own crop. An unreachable verifier drops it rather than passing it
    through -- the opposite of `_verify`'s stage-2 behaviour, because here the
    unverified answer is known to be mostly wrong.

    Confirm, never relabel. Measured 2026-09-17 on the 9 graded frames: the 7 review
    boxes the VLM RELABELLED into another requested class were all wrong -- "28s"
    countdown text -> air_defense, two hero/UI cards -> x_bow, a real X-Bow ->
    air_defense. Handed junk, the verifier picks the nearest allowed label. Same-label
    confirmations are good but not perfect: 17 true / 2 false over two runs (the
    verifier is stochastic), recovering lava-skin ADs and X-Bows at 0.42-0.79. On an
    unseen live base it confirmed the one true review box and rejected both junk ones.
    """
    boxes = [b for b in yolo.detect(frame) if b.label in classes]
    sure = [Detection(b.label, b.confidence, b.x1, b.y1, b.x2, b.y2, source="yolo")
            for b in boxes if b.confidence >= yolo.ACCEPT_CONF]
    review = [Detection(b.label, b.confidence, b.x1, b.y1, b.x2, b.y2, source="yolo")
              for b in boxes if b.confidence < yolo.ACCEPT_CONF]
    if not verify or not review:
        return sure
    with ThreadPoolExecutor(max_workers=workers) as pool:
        checked = list(pool.map(lambda d: _verify(frame, d), review))
    confirmed = []
    for asked, d in zip(review, checked):
        if d is None or not d.verified or d.label != asked.label:
            continue
        # The detector's NMS is per class, so a second-class box can sit on a building
        # already accepted under its right name.
        if any(_iou(d, s) > IOU_CROSS for s in sure + confirmed):
            continue
        confirmed.append(Detection(d.label, d.confidence, d.x1, d.y1, d.x2, d.y2,
                                   verified=True, source="yolo"))
    return sure + confirmed


def locate_buildings(frame: np.ndarray, classes=DEFAULT_CLASSES, *,
                     verify: bool = True, workers: int = 6,
                     detector: str = "hybrid") -> list[Detection]:
    """Find `classes` in a village frame. Returns native-pixel Detections.

    `detector="hybrid"` answers `FAST_CLASSES` locally (stage 0) and sends only the
    rest through stages 1-4; `detector="vlm"` sends everything through stages 1-4.

    `verify=False` skips stage 4: ~3x cheaper and ~5 s faster, at 86% precision
    instead of 100% (measured, see module docstring) for the VLM classes. For stage 0
    it means "return only boxes at `yolo.ACCEPT_CONF` or above", which stays at 74/75
    precision. Choosing a deploy or spell target goes through `deploy_targets`, not here.
    """
    unknown = set(classes) - set(CLASS_MARKS)
    if unknown:
        raise ValueError(f"unknown classes: {sorted(unknown)}")
    if detector not in DETECTORS:
        raise ValueError(f"unknown detector {detector!r}; expected one of {DETECTORS}")
    fast = set(classes) & FAST_CLASSES if detector == "hybrid" else set()
    slow = tuple(c for c in classes if c not in fast)

    out = _locate_fast(frame, fast, verify=verify, workers=workers) if fast else []
    if not slow:
        return out
    bounds = base_bounds(frame)
    tiles = _tiles(bounds, frame.shape)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        found = list(pool.map(lambda t: _detect_tile(frame, t, slow), tiles))
    kept = _nms([d for tile in found for d in tile])
    if not verify:
        return out + kept
    with ThreadPoolExecutor(max_workers=workers) as pool:
        checked = list(pool.map(lambda d: _verify(frame, d), kept))
    # Stage 4 may relabel a slow-class box into a fast class; stage 0 already owns those,
    # so keeping it would return the same Air Defense twice.
    return out + [d for d in checked if d is not None and d.label not in fast]


def deploy_targets(frame: np.ndarray,
                   classes=("air_defense", "x_bow", "inferno_tower")) -> list[Detection]:
    """Buildings to aim troops or spells at: the local detector ONLY, >= ACCEPT_CONF.

    Owner's decision 2026-09-17: targeting uses the model alone. Measured on the 9
    graded frames it is the most precise path -- 74/75 vs 82/85 with the VLM verify and
    79/89 for the VLM pipeline -- in 0.09 s with no API call, and it was 10/10 on an
    unseen live base. The price is recall (AD 27/31: lava-skin ADs score below the
    line), accepted because a false Air Defense burns 4 Lightning for nothing.

    Refuses any class the detector was not graded on, rather than quietly sending it
    to the VLM stages: a caller that wants `town_hall` must ask `locate_buildings` and
    own that choice.
    """
    other = set(classes) - FAST_CLASSES
    if other:
        raise ValueError(f"deploy targeting is model-only; not graded for {sorted(other)}")
    return locate_buildings(frame, classes, verify=False, detector="hybrid")


_OVERLAY_BGR = {
    "air_defense": (0, 0, 255), "x_bow": (255, 255, 0),
    "inferno_tower": (0, 140, 255), "town_hall": (255, 255, 255),
    "loot_bubble": (255, 0, 255),
}


def draw(frame: np.ndarray, dets: list[Detection]) -> np.ndarray:
    """Boxes burned onto a copy of the frame. The verification artefact: the repo
    contract is that a detection is graded by looking at it, not by counting it."""
    out = frame.copy()
    for d in dets:
        colour = _OVERLAY_BGR.get(d.label, (160, 160, 160))
        cv2.rectangle(out, (d.x1, d.y1), (d.x2, d.y2), colour, 3)
        cv2.putText(out, d.label, (d.x1, max(18, d.y1 - 6)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, colour, 2, cv2.LINE_AA)
    return out
