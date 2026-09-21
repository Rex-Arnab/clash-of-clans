"""Battle-side helpers: fast frame capture, battle-screen detection, entry.

Everything here was measured against the live game on 2026-09-08/09. The
numbers in the docstrings are real measurements, not estimates -- see TODO.md
"Attack research" for the full record.

Nothing in this module decides WHERE to deploy. That problem is unsolved: see
the attack research notes before trying again.
"""

from __future__ import annotations

import subprocess
import time

import cv2
import numpy as np

from . import config
from .device import Device

# --- battle HUD, NATIVE coords ---------------------------------------------
# Measured off live battle frames. The loot/resource panels are deliberately
# NOT listed: taps under them were observed to deploy normally. These three
# are the ones that actually swallow a tap.
BATTLE_HUD: list[tuple[int, int, int, int]] = [
    (0, 880, 2392, 1080),      # troop card bar
    (60, 750, 1150, 870),      # End Battle / Surrender / Boost buttons
    (2020, 660, 2392, 850),    # "Next" button
]

# Troop-card centres along the bar, left to right, at CARD_Y.
CARD_Y = 975
CARD_X = [445, 588, 708, 828, 948, 1067, 1187, 1306, 1426, 1545, 1665]

# Where the game reports a refused deploy: "YOU CANNOT DEPLOY TROOPS ON THE
# RED AREA!". Useful as a signal that *a* deploy failed, but it persists for
# seconds so it cannot attribute which one -- use the troop-card count instead.
REFUSAL_BANNER = (512, 18, 1880, 70)


def in_battle(frame: np.ndarray) -> bool:
    """True when a battle screen is up, keyed on the red End Battle button.

    This is the reliable "did we actually enter a battle" check. Three probe
    runs silently entered no battle at all and produced plausible-looking but
    entirely fabricated results before this assertion existed.
    """
    roi = frame[770:850, 110:340]
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    mask = (cv2.inRange(hsv, (0, 120, 90), (9, 255, 255)) |
            cv2.inRange(hsv, (170, 120, 90), (180, 255, 255)))
    return int(mask.sum() // 255) > 1200


def troop_badge(frame: np.ndarray, slot: int = 0) -> np.ndarray:
    """The 'xN' count badge on a troop card, for detecting a successful deploy.

    A deploy is confirmed by this patch CHANGING, not by any success message.
    Compare against a reference taken just before the tap.
    """
    x = CARD_X[slot]
    return frame[886:934, x - 29:x + 21].astype(np.int16)


def deploy_landed(before: np.ndarray, after: np.ndarray, thresh: float = 6.0) -> bool:
    return float(np.mean(np.abs(after - before))) > thresh


class RawCapture:
    """High-rate frame recorder: device-side raw screencap, pulled afterwards.

    `screenrecord` is BLOCKED on this device (ColorOS/SELinux denies it even
    where `touch` succeeds), and `screencap -p` manages only 0.61 fps because
    of on-device PNG encoding. Raw screencap hits **6.5 fps (154 ms/frame)** at
    10.3 MB/frame, and `adb pull` runs at 12.3 MB/s -- so the winning shape is
    capture raw on-device during the battle, pull a subsample afterwards.

    This is the only way to see events between decisions: at one frame per
    ~12 s the whole first-wave deploy is invisible.
    """

    DIR = "/data/local/tmp"

    def __init__(self, device: Device, max_frames: int = 400) -> None:
        self.device = device
        self.max_frames = max_frames
        self._proc: subprocess.Popen | None = None
        self.t0 = 0.0

    def start(self) -> None:
        self.device.shell(f"rm -f {self.DIR}/f*.bin {self.DIR}/STOP")
        loop = (f"i=0; while [ $i -lt {self.max_frames} ]; do "
                f"if [ -f {self.DIR}/STOP ]; then break; fi; "
                f"screencap {self.DIR}/f${{i}}.bin; i=$((i+1)); done")
        self._proc = subprocess.Popen(
            ["adb", "-s", self.device.addr, "shell", loop],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.t0 = time.time()

    def stop(self) -> int:
        """Stop recording; returns the frame count captured."""
        self.device.shell(f"touch {self.DIR}/STOP")
        if self._proc is not None:
            try:
                self._proc.wait(timeout=40)
            except subprocess.TimeoutExpired:
                self._proc.kill()
        return self.count()

    def count(self) -> int:
        out = self.device.shell(f"ls {self.DIR}/f*.bin 2>/dev/null | wc -l").strip()
        return int(out or 0)

    def fps(self, frames: int | None = None) -> float:
        frames = self.count() if frames is None else frames
        elapsed = max(time.time() - self.t0, 1e-6)
        return frames / elapsed

    def pull(self, index: int, scale: float = 0.5) -> np.ndarray | None:
        """Pull one frame and decode it. Raw layout: 12-byte header, then RGBA."""
        tmp = f"/tmp/coc_raw_{index}.bin"
        r = subprocess.run(["adb", "-s", self.device.addr, "pull",
                            f"{self.DIR}/f{index}.bin", tmp],
                           capture_output=True, timeout=90)
        if r.returncode != 0:
            return None
        buf = np.fromfile(tmp, dtype=np.uint8)
        w, h, _ = np.frombuffer(buf[:12], dtype=np.uint32)
        img = cv2.cvtColor(buf[-(int(w) * int(h) * 4):].reshape(int(h), int(w), 4),
                           cv2.COLOR_RGBA2BGR)
        if scale != 1.0:
            img = cv2.resize(img, (int(int(w) * scale), int(int(h) * scale)))
        return img

    def cleanup(self) -> None:
        self.device.shell(f"rm -f {self.DIR}/f*.bin {self.DIR}/STOP")


def grab_raw(device: Device, retries: int = 6) -> np.ndarray | None:
    """One full-resolution frame, retrying past the transient portrait frame.

    Screen transitions briefly report 1080x2392; `capture._canonicalise`
    correctly refuses those, but with no retry a single transient kills a run.
    The game has NOT left the foreground when this happens.
    """
    for _ in range(retries):
        png = device.shell_bytes("screencap -p", timeout=60)
        img = cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_COLOR)
        if img is not None and img.shape[1] == config.SCREEN_W:
            return img
        time.sleep(1)
    return None


# --- multiplayer entry ------------------------------------------------------
ATTACK_BUTTON = (209, 956)      # home village; inside NO_TAP_ZONES by design
FIND_A_MATCH = (414, 800)       # costs 1400 gold
ARMY_CONFIRM = (1955, 981)      # "Attack!" on the army-review screen
RETURN_HOME = (1196, 929)
OKAY_BUTTON = (1206, 921)       # dismisses the Star Bonus popup


def enter_multiplayer(device: Device) -> np.ndarray | None:
    """Attack -> Find a Match -> (army review) -> battle. Returns the frame.

    The army-review screen does NOT always appear. When it is skipped, tapping
    ARMY_CONFIRM lands in the battle TROOP BAR and burns spells -- observed
    live. So the screen is checked before the confirm tap rather than assumed.

    Taps here use tap_raw deliberately: the Attack button sits inside
    NO_TAP_ZONES, which exists to stop the COLLECT flow wandering into attacks.
    """
    device.tap_raw(*ATTACK_BUTTON)
    time.sleep(3.5)
    device.tap_raw(*FIND_A_MATCH)
    time.sleep(6.0)
    frame = grab_raw(device)
    if frame is None:
        return None
    if not in_battle(frame):
        device.tap_raw(*ARMY_CONFIRM)
        time.sleep(13)
        frame = grab_raw(device)
    return frame
