"""Static configuration for the Clash of Clans automation harness.

Everything here is device- and account-specific. It is deliberately a plain
module of constants rather than a config file: there is exactly one device and
one account, and a config loader would be indirection without a second caller.
"""

from __future__ import annotations

from pathlib import Path

# --- Device identity -------------------------------------------------------
# The serial is the stable anchor. The wireless-debugging host:port is NOT
# stable (Android reassigns the port on reboot), so it is never hardcoded --
# see device.discover().
DEVICE_SERIAL = "EQEMVG6HSOUO9DT4"
MDNS_SERVICE = "_adb-tls-connect._tcp"

PACKAGE = "com.supercell.clashofclans"
LAUNCH_ACTIVITY = f"{PACKAGE}/com.supercell.titan.GameApp"

# --- Screen geometry -------------------------------------------------------
# MEASURED, not assumed: Clash of Clans forces landscape. With the game
# foregrounded, dumpsys reports mBounds=Rect(0,0-2392,1080) at ROTATION_270.
# The launcher is portrait (1080x2392); the game is the transpose. Every
# coordinate in this project is in LANDSCAPE space.
SCREEN_W, SCREEN_H = 2392, 1080

# The density override the HUD is laid out against. If this ever changes, every
# fixed ROI and every template silently shifts -- so it is asserted at session
# start rather than trusted.
EXPECTED_DENSITY = 360

# Perception runs at NATIVE resolution. An earlier draft downscaled 2:1, but
# HUD digits are only ~25px tall natively and halving them costs real accuracy,
# while the saving buys nothing: frames arrive ~8.7s apart, so a 20ms match is
# free. Working 1:1 also removes the coordinate-scaling step entirely, which is
# the single most common source of "taps land at a constant offset" bugs.
# Phase 4 streaming may reintroduce a downscale; templates would be recut then.
CAPTURE_W, CAPTURE_H = SCREEN_W, SCREEN_H
CAPTURE_SCALE = 1.0

# --- Safety ----------------------------------------------------------------
# Skip a run below this battery level unless the phone is on a charger.
MIN_BATTERY_PCT = 25

# Geometric no-tap zones in CAPTURE_SIZE space, as (x1, y1, x2, y2).
# A tap resolving inside one of these is refused outright, whatever the
# matcher believes it found. Accidental gem spend is the costliest failure
# mode, so this is enforced below the flow layer and cannot be opted out of.
# Populated in Phase 0 once the real HUD positions are captured.
NO_TAP_ZONES: list[tuple[int, int, int, int]] = []

# --- Input humanisation ----------------------------------------------------
# Taps land at a random point inside the matched element rather than its exact
# centre, and pauses vary. Machine-perfect input is the easiest bot signature.
TAP_JITTER_FRAC = 0.25          # of the matched box's half-extent
MIN_ACTION_DELAY = 0.35         # seconds
MAX_ACTION_DELAY = 1.10

# --- Vision ----------------------------------------------------------------
TEMPLATE_THRESHOLD = 0.87       # cv2.matchTemplate TM_CCOEFF_NORMED
DIGIT_THRESHOLD = 0.80

# --- Paths -----------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
TEMPLATES = ASSETS / "templates"
DIGITS = ASSETS / "digits"
MODELS = ASSETS / "models"
RUNS = ROOT / "runs"
RUN_LOG = RUNS / "runs.jsonl"

# How many recent runs keep their screenshots on disk.
SCREENSHOT_RETENTION_RUNS = 40

# --- OpenRouter (Tier 3 fallback) ------------------------------------------
# google/gemini-3-flash-preview: 1M context, image input, $0.50/M prompt.
# Tier 3 only fires on screens Tier 1 could not classify, so volume should stay
# low and decay as its answers are written back as templates.
VLM_MODEL = "google/gemini-3-flash-preview"
VLM_ENABLED = True
