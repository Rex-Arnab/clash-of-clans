"""Screen-state classification and the navigation panic path.

The design rule here is that the harness never acts on a screen it cannot
name. Blind-tapping an unrecognised screen is how automation buys gems, so an
unknown state stops the run instead.

The disconnect dialog is treated as a normal transition rather than an error:
Clash of Clans drops an idle session, and this harness idles for an hour
between runs by design, so "reload the game" is the expected first step of
almost every scheduled run.
"""

from __future__ import annotations

import time
from enum import Enum

import numpy as np

from .. import config
from ..capture import ScreencapSource
from ..device import DeviceBlocked
from . import templates as T


class Screen(str, Enum):
    HOME_VILLAGE = "home_village"
    BUILDER_BASE = "builder_base"
    DISCONNECTED = "disconnected"
    UNKNOWN = "unknown"


def _matches(frame: np.ndarray, name: str, threshold: float) -> T.Match | None:
    hits = T.find_all(frame, name, threshold)
    return hits[0] if hits else None


def classify(frame: np.ndarray) -> Screen:
    """Name the current screen, cheapest and most specific check first."""
    if _matches(frame, "dlg_reload_game", 0.10) is not None:
        return Screen.DISCONNECTED
    # The four resource counters are only laid out and legible on a village
    # screen, so parsing them is the village proof. See _village_hud_present:
    # their mere BRIGHTNESS is not proof, which is what this used to test.
    if _village_hud_present(frame):
        return Screen.HOME_VILLAGE
    return Screen.UNKNOWN


def _village_hud_present(frame: np.ndarray) -> bool:
    """True when the village's resource counters are actually READABLE.

    This used to test only that the four ROIs were bright, on the assumption
    that any modal dims the village behind it. That assumption is false.
    Measured 2026-09-08 against live panels: League Overview and My Army leave
    all four ROIs above the brightness gate while covering the village, so the
    old check reported HOME_VILLAGE with a modal open -- and ensure_village()
    would hand that modal to a flow as if it were the village.

    Requiring the digits to parse separates them with no overlap at all:

        classify()      readable/4   frames
        home_village    4/4          22
        disconnected    0/4           2
        (League, My Army, Events, Attack Log, all 0/4)

    Three of four, not four, deliberately keeps the slack the brightness test
    had: one ambiguous glyph should not push a real village into the panic
    path, and with a 4-vs-0 margin the slack costs no discrimination.

    Costs one digit pass (~14 ms) against a ~8 s frame grab.
    """
    from .digits import default_atlas, read_resources

    values = read_resources(frame, default_atlas())
    return sum(v is not None for v in values.values()) >= 3


def which_base(frame: np.ndarray) -> Screen:
    """Which village is on screen: HOME_VILLAGE, BUILDER_BASE, or UNKNOWN.

    `classify()` cannot answer this and must not be asked to: it has no Builder
    Base check at all, so it returns HOME_VILLAGE on a Builder Base frame -- the
    Home Village ROIs still land on legible digits there and its >=3-of-4 gate
    passes. That is a real, still-open bug; this function is the way around it and
    `classify()` is deliberately left alone.

    The discriminator is the FOURTH ROW. The Home Village HUD is
    gold/elixir/dark/gems; the Builder Base has only gold/elixir/gems and every
    row sits ~100 px higher (see `builder_base` module docstring). So the Home
    Village `gems` ROI at y 342-378 is legible in the Home Village and in nothing
    else. It is a HUD fact, which is what makes it camera-independent -- unlike
    the boat, which "sat at (895,555) only for one particular pan".

    A legible gems row is therefore sufficient on its own for HOME_VILLAGE, and
    that slack matters: measured live on 2026-09-18 a real Home Village frame read
    gold/dark/gems fine but `elixir` came back None, and an earlier version of this
    function -- which demanded gold AND elixir before looking at gems -- called it
    UNKNOWN. `classify()` keeps the same kind of slack ("three of four, not four")
    for the same reason.

    Fails closed, and that is the load-bearing property. Without a gems row we
    require BOTH gold and elixir before naming the Builder Base; anything less is
    a battle, a result screen or a village under a popup, and the answer is
    UNKNOWN -- never a base. Measured 2026-09-18 over 68 frames:

        frame set              n    result                          wrong base
        Builder Base village   28   24 BUILDER_BASE, 4 UNKNOWN      0
        Builder Base battle    27   27 UNKNOWN                      0
        Home Village (+live)   13    5 HOME_VILLAGE, 8 UNKNOWN      0

    Zero frames were ever called the wrong base. The UNKNOWN cases are occluded
    HUDs, battle screens and non-village captures; a caller settles and re-grabs
    rather than guessing. Costs one digit pass (~14 ms).
    """
    from .digits import default_atlas, read_resources

    v = read_resources(frame, default_atlas())
    if v.get("gems") is not None:
        # A legible FOURTH row exists. Only the Home Village has one.
        return Screen.HOME_VILLAGE
    if v.get("gold") is not None and v.get("elixir") is not None:
        return Screen.BUILDER_BASE
    return Screen.UNKNOWN


def ensure_village(device, source: ScreencapSource, tapper,
                   log=None, max_steps: int = 4) -> np.ndarray:
    """Drive the game to the Home Village, or refuse to continue.

    Returns the frame that proved we got there. Raises DeviceBlocked rather
    than improvising if the screen stays unrecognised.
    """
    frame = source.grab()
    for step in range(max_steps):
        state = classify(frame)
        if log:
            log.event("classify", step=step, state=state.value)

        if state is Screen.HOME_VILLAGE:
            return frame

        if state is Screen.DISCONNECTED:
            m = _matches(frame, "dlg_reload_game", 0.10)
            ox, oy = T.manifest()["templates"]["dlg_reload_game"]["tap_offset"]
            tapper.tap(m.x + ox, m.y + oy, label="reload_game", navigation=True)
            # Reloading replays the whole loading sequence, not just a redraw.
            time.sleep(18)
            frame = source.grab()
            continue

        # Unknown: a generic dismiss is the one safe move, then re-look.
        device.back()
        time.sleep(2.5)
        frame = source.grab()

    raise DeviceBlocked(
        f"could not reach the Home Village in {max_steps} steps; "
        "last state was not recognised, so nothing was tapped"
    )
