"""Frame sources.

Everything downstream consumes `Frame`: a BGR ndarray at exactly
(CAPTURE_H, CAPTURE_W). Keeping that one contract means a template cut today
against slow screencap frames still matches tomorrow's scrcpy frames, and the
attack loop can swap in a faster source without touching perception code.
"""

from __future__ import annotations

import time

import cv2
import numpy as np

from . import config
from .device import Device, DeviceBlocked, DeviceError

Frame = np.ndarray


class CaptureError(DeviceError):
    """A frame could not be obtained or was not the shape we require."""


def _canonicalise(img: Frame) -> Frame:
    """Validate orientation and downscale to the single working resolution.

    The game is landscape; the launcher is portrait. A portrait frame therefore
    means the game is not actually in front, which is a state we refuse to act
    on rather than silently rotate -- rotating would produce plausible-looking
    frames of the wrong screen and every tap would land somewhere arbitrary.
    """
    h, w = img.shape[:2]
    if (w, h) != (config.SCREEN_W, config.SCREEN_H):
        raise CaptureError(
            f"expected landscape {config.SCREEN_W}x{config.SCREEN_H}, got {w}x{h}. "
            "The game is probably not in the foreground."
        )
    if (w, h) != (config.CAPTURE_W, config.CAPTURE_H):
        img = cv2.resize(
            img, (config.CAPTURE_W, config.CAPTURE_H), interpolation=cv2.INTER_AREA
        )
    return img


class ScreencapSource:
    """`adb exec-out screencap -p`. ~5 s/frame over wifi -- lossless, simple.

    Correct for the village loop, where decisions are seconds apart. Too slow
    for battles; see ScrcpySource.
    """

    name = "screencap"

    def __init__(self, device: Device) -> None:
        self.device = device

    def grab(self) -> Frame:
        png = self.device.shell_bytes("screencap -p", timeout=45)
        if not png:
            raise CaptureError("screencap returned no data")
        img = cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            raise CaptureError("screencap output was not a decodable image")
        return _canonicalise(img)

    def close(self) -> None:  # symmetry with ScrcpySource
        pass


def assert_geometry(device: Device) -> None:
    """Fail fast if the device no longer matches what templates were cut against.

    A density change silently shifts every HUD element, so it is checked rather
    than assumed -- a wrong-but-plausible frame is worse than no frame.
    """
    out = device.shell("wm density")
    density = None
    for line in out.splitlines():
        if "Override density:" in line:
            density = int(line.split(":")[1].strip())
    if density is None:
        for line in out.splitlines():
            if "Physical density:" in line:
                density = int(line.split(":")[1].strip())
    if density != config.EXPECTED_DENSITY:
        raise DeviceBlocked(
            f"display density is {density}, templates were cut at "
            f"{config.EXPECTED_DENSITY}. Every fixed region would be wrong."
        )


def wait_for_game(device: Device, timeout: float = 90.0) -> None:
    """Launch the game if needed and block until it is actually in front.

    Waits on the landscape window bounds rather than on the process existing:
    the process appears within a second, but the surface is not laid out until
    well into the loading screen, and a frame grabbed before then is portrait.
    Both polls go through `shell_grep`: a grep miss means "not yet", and through
    plain `shell()` the first miss on a cold start raised instead of waiting.
    """
    if device.app_pid() is None:
        device.launch_app()
    deadline = time.time() + timeout
    while time.time() < deadline:
        out = device.shell_grep("dumpsys activity activities | grep topResumedActivity")
        if config.PACKAGE in out:
            bounds = device.shell_grep(
                "dumpsys window | grep -m1 'mAppBounds=Rect(0, 0 - 2392, 1080)'"
            )
            if bounds.strip():
                return
        time.sleep(2.0)
    raise DeviceBlocked(
        f"{config.PACKAGE} did not reach a landscape foreground state in {timeout}s"
    )
