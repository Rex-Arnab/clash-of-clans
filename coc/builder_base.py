"""Builder Base: entry, loot bubbles, battle boundary and deploy planning.

Measured against the live game on 2026-09-09. The Builder Base is a DIFFERENT
screen space from the Home Village -- its HUD rows, safe zones and battle rules
all differ -- so nothing here may be reused from `coc.safety` or
`coc.vision.templates` without re-measuring. See `coc/flows/CLAUDE.md`.

What is validated and what is not is stated per function. Do not promote an
unvalidated number into a flow.
"""

from __future__ import annotations

import math

import cv2
import numpy as np

# --- HUD, NATIVE 2392x1080 --------------------------------------------------
# The Builder Base has THREE resource rows (gold, elixir, gems); the Home
# Village has four (gold, elixir, dark, gems). Every row therefore sits ~100 px
# HIGHER here, which is why the Home Village zones do not transfer.
#
# MEASURED on a live Builder Base frame:
#   gem "+" buy button   (2003,240)-(2053,290)   centre (2027,264)
# `safety.NO_TAP_ZONES` protects (1950,300,2392,430), which is BELOW this --
# so in the Builder Base the gem-purchase button is NOT covered by the Home
# Village interlock.
GEM_BUY_ZONE = (1990, 225, 2075, 305)

# Resource counters, MEASURED on the 28 stored Builder Base village frames
# (2026-09-18). These are DELIBERATELY not imported from `digits.RESOURCE_ROIS`,
# even where the numbers coincide: a Home Village constant in Builder Base code
# is a bug even when it happens to work, so these were read off Builder Base
# frames and belong to this module.
#
# What the measurement actually showed, against the module docstring above: gold
# and elixir do NOT move -- they sit at the same y as the Home Village. Only the
# GEMS row is ~100 px higher, because it takes the slot the Home Village spends
# on dark elixir. That is why running `read_resources()` on a Builder Base frame
# returns a plausible, WRONG answer: it reports the gem count (809) under the key
# "dark". There is no dark elixir in the Builder Base.
BB_RESOURCE_ROIS: dict[str, tuple[int, int, int, int]] = {
    "gold":   (1980,  42, 2205,  80),
    "elixir": (1980, 142, 2205, 180),
    "gems":   (1980, 242, 2205, 280),
}


def read_bb_resources(frame: np.ndarray, atlas) -> dict[str, int | None]:
    """Read the THREE Builder Base HUD counters. Unreadable fields come back None.

    Mirrors `digits.read_resources` -- same atlas, same fail-closed rule, an
    ambiguous glyph is None and never a guess -- but over this base's own ROIs
    and with no `dark` key, because the Builder Base has no dark elixir.

    Validated 2026-09-18 on all 28 stored Builder Base village frames: every
    readable gold value matches the b1-b14 progression in TODO.md exactly, and
    `gems` reads 809 throughout (the account's gem count, unchanged across those
    battles). See `coc/vision/screens.which_base` for telling the bases apart.
    """
    from .vision.digits import UnreadableNumber, read_number

    out: dict[str, int | None] = {}
    for name, roi in BB_RESOURCE_ROIS.items():
        try:
            out[name] = read_number(frame, roi, atlas)
        except UnreadableNumber:
            out[name] = None
    return out

BB_NO_TAP_ZONES: list[tuple[int, int, int, int]] = [
    GEM_BUY_ZONE,
    (60, 845, 340, 1080),      # Attack! button
    (2040, 830, 2392, 1080),   # Shop
    (325, 862, 488, 1062),     # the 2x-elixir / shield button (also in Home Village)
]

# Battle-screen gem spends. MEASURED: Boost Army (353,715)-(649,788).
# Boost Heroes sits immediately right of it on the same row.
BB_BATTLE_NO_TAP: list[tuple[int, int, int, int]] = [
    (330, 700, 1000, 800),     # Boost Army / Boost Heroes -- both cost gems
    (0, 860, 2392, 1080),      # troop card bar
    (60, 700, 340, 800),       # Surrender / End Battle
    (2150, 560, 2392, 700),    # 1x/2x battle speed toggle
]

# Troop cards along the bar. Card 0 is the Battle Machine, 1..6 the troops.
BB_CARD_Y = 973
BB_CARD_X = [431, 600, 752, 904, 1056, 1207, 1359]
# Builder Base 2.0 is TWO-STAGE: three-starring stage 1 opens a second base with
# fresh cards, which appear in these two extra slots. The bar holds 8, not 7.
BB_CARD_X_STAGE2 = [1531, 1676]

RETURN_HOME = (1195, 909)      # "Return Home" on the battle result screen
FIND_NOW = (1663, 709)         # "Find Now!" on the Start Attack dialog -- FREE
ATTACK_BUTTON = (206, 957)     # same coordinate as the Home Village button


# --- loot bubbles -----------------------------------------------------------
# The bubble sprite (olive rounded square + downward tail) is IDENTICAL in the
# Home Village and the Builder Base; only the inner icon differs. It does NOT
# render at a fixed screen size -- it scales with camera zoom, which is why a
# single-scale template match is unreliable. Keying on the olive frame colour
# and the frame/interior contrast is scale-tolerant.
_OLIVE_LO, _OLIVE_HI = (30, 25, 155), (38, 120, 240)
_BW, _BH = 51, 55              # frame box at the zoom levels observed


def _olive_mask(frame: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    m = cv2.inRange(hsv, _OLIVE_LO, _OLIVE_HI)
    return cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))


def _score(mask: np.ndarray, x: int, y: int) -> float:
    """Olive fraction on the frame ring MINUS olive fraction inside it.

    A real bubble has an olive border around a coloured icon, so the border is
    olive and the interior is not. A flat pale UI panel scores near zero or
    negative -- an open building menu measured -0.531.
    """
    patch = mask[y:y + _BH, x:x + _BW]
    if patch.shape != (_BH, _BW):
        return 0.0
    border = np.zeros((_BH, _BW), np.uint8)
    border[0:9, :] = 1; border[-9:, :] = 1; border[:, 0:9] = 1; border[:, -9:] = 1
    inner = np.zeros((_BH, _BW), np.uint8)
    inner[16:39, 14:37] = 1
    return float((patch[border == 1] > 0).mean() - (patch[inner == 1] > 0).mean())


def find_bubbles(frame: np.ndarray, min_score: float = 0.35) -> list[tuple[int, int, float]]:
    """Collectable loot bubbles as (x, y, score), tap point at the centre.

    VALIDATED live: on a Builder Base frame with three bubbles this returned
    exactly three, and tapping them one at a time went 3 -> 2 -> 1 -> 0 with
    gold +2,448, elixir +2,475 and gems +10 on the counters.
    """
    mask = _olive_mask(frame)
    n, _, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    out = []
    for i in range(1, n):
        x, y, w, h, a = stats[i]
        if a > 900 and 45 <= w <= 62 and 45 <= h <= 82:
            s = _score(mask, x, y)
            if s >= min_score:
                out.append((int(x + _BW // 2), int(y + _BH // 2), round(s, 3)))
    return out


# --- battle: boundary and deploy planning -----------------------------------
def base_hull(frame: np.ndarray) -> np.ndarray | None:
    """Convex hull of the enemy base's red deploy boundary.

    This works in the Builder Base and FAILED in the Home Village: here the
    boundary sits on plain green grass, whereas a maxed Home Village base is
    full of red roofs and decorations that saturate the mask (5/13 detection).
    """
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    m = (cv2.inRange(hsv, (0, 90, 80), (10, 255, 255)) |
         cv2.inRange(hsv, (168, 90, 80), (180, 255, 255)))
    m[860:, :] = 0      # troop bar
    m[0:110, :] = 0     # top HUD
    ys, xs = np.nonzero(m)
    if len(xs) < 500:
        return None
    return cv2.convexHull(np.column_stack([xs, ys]).astype(np.int32))


def deploy_points(hull: np.ndarray, angles: list[int], pad: int = 75,
                  y_max: int = 845) -> list[tuple[int, int]]:
    """Points `pad` px outside the hull along each screen angle (degrees).

    Deploys must land OUTSIDE the red boundary. `y_max` keeps a point clear of
    the troop bar; note that clamping collapses several angles onto one line,
    so prefer angles that do not need clamping.
    """
    M = cv2.moments(hull)
    cx, cy = int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"])
    pts = []
    for deg in angles:
        a = math.radians(deg)
        dx, dy = math.cos(a), math.sin(a)
        last, r = 0, 0
        while r < 1400:
            x, y = int(cx + dx * r), int(cy + dy * r)
            if not (0 <= x < 2392 and 0 <= y < 1080):
                break
            if cv2.pointPolygonTest(hull, (x, y), False) >= 0:
                last = r
            r += 4
        r = last + pad
        pts.append((max(20, min(2372, int(cx + dx * r))),
                    max(120, min(y_max, int(cy + dy * r)))))
    return pts

def in_bb_battle(frame: np.ndarray) -> bool:
    """A Builder Base battle is still on screen (red Surrender / End Battle).

    GUARD THIS BEFORE EVERY TIMED TAP. On 2026-09-09 a timed ability batch kept
    firing after the battle had already ended; the taps landed on the result
    screen and walked into the Season Pass shop, which carries a real-money
    offer. Nothing was purchased, but no timed tap may be sent on faith again:
    a battle ends when it ends, not when the timer says it should.
    """
    roi = frame[715:790, 60:340]
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    m = (cv2.inRange(hsv, (0, 110, 90), (9, 255, 255)) |
         cv2.inRange(hsv, (170, 110, 90), (180, 255, 255)))
    return int(m.sum() // 255) > 900


def modal_present(frame: np.ndarray) -> bool:
    """A dialog panel (Task Cards, offers) is covering the village.

    Keyed on the panel's flat brown fill, NOT on red pixels in the top-right:
    the Builder Base has a red-and-white striped boat parked there, and a
    red-pixel test reported a modal on clean frames. Measured brown fraction:
    0.695 with a modal, 0.003-0.083 without.
    """
    c = frame[150:820, 800:1600]
    hsv = cv2.cvtColor(c, cv2.COLOR_BGR2HSV)
    return float(cv2.inRange(hsv, (5, 30, 35), (25, 140, 130)).mean()) / 255.0 > 0.30

# --- deploy planning: fit every troop, maximise separation -------------------
TANTRUM_PX = 190   # 4.5 tiles at the upper end of the measured 105-190 px range


def _greedy(order, sep, n):
    import math
    chosen = []
    for a, p in order:
        if not chosen or min(math.hypot(p[0] - q[0], p[1] - q[1]) for _, q in chosen) >= sep:
            chosen.append((a, p))
        if len(chosen) == n:
            break
    return chosen


def plan_deploy(hull, n=6, valid=None):
    """n deploy points on one flank, maximising the minimum pairwise separation.

    Returns (points, achieved_min_sep, mode).

    Baby Dragons get the Tantrum bonus (40-160% extra damage) only while >=4.5
    tiles from other AIR units, which is TANTRUM_PX on screen. A fixed threshold
    fitted only 5 of 6 on run r7 and the sixth was never deployed, so this
    searches downward for the largest separation at which all n still fit and
    tries every start offset rather than walking greedily from one end.

    NOTE: on most bases one flank cannot hold 6 dragons at >=TANTRUM_PX -- the
    achieved separation is returned so a caller can log what it actually got.
    Keeping the group on one flank protects the Battle Machine, and BM survival
    was measured to matter far more than the Tantrum bonus (see TODO.md r5-r7).

    Validated offline on 5 saved bases (6/6 on every one); NOT yet battle-tested.
    """
    import math
    if valid is None:
        return [], 0, "none"
    if not valid:
        return [], 0, "none"
    angles = {a for a, _ in valid}
    by = {a: p for a, p in valid}
    best, bl = [], -1
    for s0 in angles:
        run, a = [], s0
        while (a % 360) in angles and len(run) < 72:
            run.append(a % 360); a += 5
        if len(run) > bl:
            bl, best = len(run), run
    arc = [(a, by[a]) for a in best]
    for order, mode in ((arc, "arc"), (sorted(valid), "perimeter")):
        for sep in range(500, 40, -10):
            for st in range(len(order)):
                c = _greedy(order[st:] + order[:st], sep, n)
                if len(c) == n:
                    pts = [p for _, p in c]
                    # n == 1 has no pairs; min() over an empty iterable raises.
                    # A single unit is trivially past any separation threshold.
                    ms = min((math.hypot(pts[i][0] - pts[j][0], pts[i][1] - pts[j][1])
                              for i in range(n) for j in range(i + 1, n)),
                             default=float("inf"))
                    return c, ms, mode
    c = _greedy(arc, 40, n)
    return c, 0, "degraded"


# --- defence knowledge base -------------------------------------------------
def load_defences() -> dict:
    """The Builder Base defence table (assets/bb_defenses.json).

    Sourced from the wiki, one defence at a time, on 2026-09-09. Every entry
    records `targets` as ground / air / both / none, plus range in tiles.
    Nothing in it was guessed: unconfirmed fields are recorded as null and the
    Cannon carries an explicit source caveat.
    """
    import json
    from pathlib import Path
    p = Path(__file__).resolve().parent.parent / "assets" / "bb_defenses.json"
    return json.loads(p.read_text())


def threatens(unit: str, table: dict | None = None) -> list[str]:
    """Defences that can hit `unit` ("air" for dragons, "ground" for the BM).

    The X-Bow is mode-dependent and is ALWAYS included: it cannot be resolved
    statically, so it fails closed into both lists.
    """
    t = (table or load_defences())["defences"]
    want = {unit, "both", "mode_dependent"}
    return sorted(k for k, v in t.items() if v.get("targets") in want)


def free_targets(unit: str, table: dict | None = None) -> list[str]:
    """Defences `unit` can destroy without ever being shot back at.

    Dragons (air) may kill every ground-only defence for free -- including the
    Crusher, which is the Battle Machine's worst threat. The BM (ground) may
    kill every air-only defence for free -- Firecrackers and Air Bombs, the
    dragons' worst threats. Each unit is immune to what kills the other.
    """
    other = "ground" if unit == "air" else "air"
    t = (table or load_defences())["defences"]
    return sorted(k for k, v in t.items() if v.get("targets") == other)

# --- dialog recovery --------------------------------------------------------
def green_confirm(frame: np.ndarray) -> tuple[int, int] | None:
    """Centre-screen green button, or None. NOT always a dismissal."""
    roi = frame[600:980, 700:1700]
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    m = cv2.inRange(hsv, (38, 120, 130), (85, 255, 255))
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    n, _, st, cen = cv2.connectedComponentsWithStats(m, 8)
    best = None
    for i in range(1, n):
        _, _, w, h, a = st[i]
        if a > 9000 and w > 180 and 45 < h < 160 and (best is None or a > best[0]):
            best = (a, int(cen[i][0]) + 700, int(cen[i][1]) + 600)
    return None if best is None else (best[1], best[2])


def red_close(frame: np.ndarray) -> tuple[int, int] | None:
    """Top-right red X of a dialog, or None. Always safe to tap."""
    roi = frame[120:280, 1600:2200]
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    m = (cv2.inRange(hsv, (0, 140, 120), (8, 255, 255)) |
         cv2.inRange(hsv, (172, 140, 120), (180, 255, 255)))
    n, _, st, cen = cv2.connectedComponentsWithStats(m, 8)
    for i in range(1, n):
        _, _, w, h, a = st[i]
        if a > 1800 and 45 < w < 130 and 45 < h < 130:
            return (int(cen[i][0]) + 1600, int(cen[i][1]) + 120)
    return None


def dismiss_point(frame: np.ndarray) -> tuple[int, int] | None:
    """Where to tap to clear a dialog. PREFERS the red X.

    A green centre button is not necessarily a dismissal: on the Start Attack
    panel it is "Find Now!", which STARTS a battle. Measured on real frames --
    Start Attack yields both a red X (1869,200) and a green (1578,729) "Find
    Now!", so preferring red is what stops auto-recovery from launching attacks.
    `modal_present()` misses both of these dialogs (blue Star Bonus, pale tan
    Start Attack), which is why recovery keys on the BUTTON, not the panel.
    """
    return red_close(frame) or green_confirm(frame)


def hero_ready(frame: np.ndarray) -> bool:
    """True when the hero card is in COLOUR, i.e. a hero is available to deploy.

    Builder Base 2.0 gives you BOTH heroes across the two stages: the selected
    hero (Battle Machine) in stage 1, and the OTHER one (Battle Copter) arrives
    fresh for stage 2. Run r10 deployed only the two new dragon cards (x>1450)
    and left that free Copter unused for the whole of stage 2.

    A dead/greyed hero card measures ~1.9 mean saturation; a live one ~93.0.
    """
    card = frame[890:1060, 370:495]
    return float(cv2.cvtColor(card, cv2.COLOR_BGR2HSV)[:, :, 1].mean()) > 30.0


# UNSUPPORTED BY EVIDENCE -- kept only because it is harmless. Separation does
# NOT order outcomes across the four Battle Machine runs:
#   193px -> 69%/2*,  215px -> 100%/3*,  257px -> 52%/2*,  279px -> 119%/3*
# Damage across 11 runs is mean 79%, sd 27, range 45-131. Base-to-base variance
# swamps every spacing/timing parameter at one run per configuration. Do not
# tune this without a proper A/B (~16 runs per arm for a 20-point effect).
COMFORT_PX = 240


def plan_wave(hull, valid, n_max: int = 6, comfort: int = COMFORT_PX,
              floor: int = TANTRUM_PX):
    """Largest wave whose separation is COMFORTABLE, else the largest that clears
    the bare Tantrum floor. Returns (wave, sep, n).

    `plan_deploy` alone accepts the first size clearing `floor`, so r11 took 5
    dragons at 193 px -- barely over 190 -- and managed 69%/2 stars, while r10 at
    279 px reached 119%/3 stars. Separation appears to matter more than headcount,
    so try for `comfort` first and hold the rest back as reserve.
    """
    best_floor = None
    for n in range(n_max, 2, -1):
        c, sep, _ = plan_deploy(hull, n=n, valid=valid)
        if len(c) != n:
            continue
        if sep >= comfort:
            return c, sep, n
        if sep >= floor and best_floor is None:
            best_floor = (c, sep, n)
    if best_floor:
        return best_floor
    c, sep, _ = plan_deploy(hull, n=3, valid=valid)
    return c, sep, len(c)


ALL_CARD_X = BB_CARD_X + BB_CARD_X_STAGE2   # 7 stage-1 slots + 2 stage-2 slots


def card_alive(frame: np.ndarray, slot: int) -> bool:
    """True if the troop card in `slot` is in colour (unit alive or available).

    MEASURED on live stage-2 frames: a greyed/dead card reads 0.0 mean
    saturation; every live card reads 63-158. Clean separation, no overlap.

    This says ALIVE, not DEPLOYABLE. There is no reliable visual deployable
    flag: the green ⬇⬆ badge marks a NEWLY AVAILABLE card and fades, so fresh
    deployable dragons show it during prep but NOT once the battle is running
    (verified: `live.png` had 6 deployable dragons and zero badges). Three
    detectors built on that badge each disagreed with reality.

    To deploy in stage 2, TRY EVERY SLOT instead -- a dead card no-ops, an
    on-field card merely fires its ability, and the map tap is inert without a
    selection. Calibration run confirmed all deployable units went in this way.
    """
    x = ALL_CARD_X[slot]
    card = frame[890:1060, x - 52:x + 52]
    return float(cv2.cvtColor(card, cv2.COLOR_BGR2HSV)[:, :, 1].mean()) > 30.0
