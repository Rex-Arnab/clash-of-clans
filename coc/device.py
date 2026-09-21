"""ADB transport: discovery, reconnection, input injection, power state.

The phone is attached over Android 11+ Wireless Debugging, which assigns an
ephemeral port that changes on reboot. `adb mdns services` reports nothing on
this host, but macOS `dns-sd` browses the same records fine, so rediscovery
goes through dns-sd and re-derives the address from the stable serial.
"""

from __future__ import annotations

import random
import re
import shutil
import subprocess
import time

from . import config


class DeviceError(RuntimeError):
    """The device cannot be reached, or a command genuinely failed."""


class DeviceBlocked(RuntimeError):
    """Reachable, but must not be driven right now.

    Deliberately not a DeviceError. "Blocked" is an expected, recoverable
    outcome -- low battery, screen off, game updating -- that a run should
    report and stop on. Conflating it with a hard error invites a retry loop
    that drives the phone in a state we said we would not drive it in.
    """


def _run(args: list[str], timeout: float = 30.0) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise DeviceError(f"timed out after {timeout}s: {' '.join(args)}") from exc
    except FileNotFoundError as exc:
        raise DeviceError(f"executable not found: {args[0]}") from exc


def _dns_sd(args: list[str], settle: float = 4.0) -> str:
    """Run a dns-sd query briefly and return what it printed.

    dns-sd is a streaming browser: it never exits on its own, so it is given a
    moment to report and then terminated. An empty result is normal (the phone
    may simply be off the network), not an error.
    """
    if shutil.which("dns-sd") is None:
        return ""
    proc = subprocess.Popen(
        ["dns-sd", *args], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True
    )
    try:
        time.sleep(settle)
    finally:
        proc.terminate()
        try:
            out, _ = proc.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            out, _ = proc.communicate()
    return out or ""


def _connected_addresses() -> list[str]:
    """Transports adb currently lists as `device` (not offline/unauthorized)."""
    out = _run(["adb", "devices"], timeout=15).stdout
    addrs = []
    for line in out.splitlines()[1:]:
        if "\tdevice" in line:
            addrs.append(line.split("\t", 1)[0].strip())
    return addrs


def _serial_of(addr: str) -> str | None:
    """Stable hardware serial behind a transport address, or None if dead."""
    cp = _run(["adb", "-s", addr, "shell", "getprop", "ro.serialno"], timeout=10)
    if cp.returncode != 0:
        return None
    return cp.stdout.strip() or None


def _mdns_endpoints() -> list[str]:
    """Browse mDNS for our device and resolve it to host:port candidates."""
    browse = _dns_sd(["-B", config.MDNS_SERVICE, "local"], settle=4.0)
    instances = {
        m.group(1).strip()
        for line in browse.splitlines()
        if " Add " in line and config.DEVICE_SERIAL in line
        if (m := re.search(rf"(adb-{config.DEVICE_SERIAL}\S*(?: \(\d+\))?)\s*$", line))
    }
    endpoints: list[str] = []
    for inst in instances:
        resolved = _dns_sd(["-L", inst, config.MDNS_SERVICE, "local"], settle=4.0)
        for m in re.finditer(r"can be reached at\s+(\S+?):(\d+)", resolved):
            host, port = m.group(1).rstrip("."), m.group(2)
            endpoints.append(f"{host}:{port}")
    return endpoints


class Device:
    """A connected phone. Construct via `Device.connect()`."""

    def __init__(self, addr: str) -> None:
        self.addr = addr

    # -- lifecycle ---------------------------------------------------------
    @classmethod
    def connect(cls, allow_rediscovery: bool = True) -> "Device":
        """Find the phone, preferring a transport that already works."""
        for addr in _connected_addresses():
            if _serial_of(addr) == config.DEVICE_SERIAL:
                return cls(addr)

        if not allow_rediscovery:
            raise DeviceError("device not connected and rediscovery disabled")

        for endpoint in _mdns_endpoints():
            _run(["adb", "connect", endpoint], timeout=20)
            if _serial_of(endpoint) == config.DEVICE_SERIAL:
                return cls(endpoint)

        raise DeviceError(
            f"could not reach device {config.DEVICE_SERIAL}. Check the phone is awake, "
            "on the same wifi, and that Wireless Debugging is still enabled "
            "(it switches off when the phone forgets the network)."
        )

    # -- raw commands ------------------------------------------------------
    def shell(self, cmd: str, timeout: float = 30.0) -> str:
        cp = _run(["adb", "-s", self.addr, "shell", cmd], timeout=timeout)
        if cp.returncode != 0:
            raise DeviceError(f"shell failed: {cmd}\n{cp.stderr.strip()}")
        return cp.stdout

    def shell_bytes(self, cmd: str, timeout: float = 60.0) -> bytes:
        """exec-out variant, for binary payloads such as screencap PNG data."""
        try:
            cp = subprocess.run(
                ["adb", "-s", self.addr, "exec-out", cmd],
                capture_output=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise DeviceError(f"exec-out timed out after {timeout}s: {cmd}") from exc
        if cp.returncode != 0:
            raise DeviceError(f"exec-out failed: {cmd}")
        return cp.stdout

    # -- power / readiness -------------------------------------------------
    def battery(self) -> tuple[int, bool]:
        """(level percent, is_charging)."""
        out = self.shell("dumpsys battery")
        level = int(re.search(r"^\s*level:\s*(\d+)", out, re.M).group(1))
        charging = any(
            re.search(rf"^\s*{k} powered: true", out, re.M)
            for k in ("AC", "USB", "Wireless", "Dock")
        )
        return level, charging

    def screen_on(self) -> bool:
        return "mWakefulness=Awake" in self.shell("dumpsys power")

    def wake(self) -> None:
        if not self.screen_on():
            self.shell("input keyevent KEYCODE_WAKEUP")
            time.sleep(1.0)
        # Dismiss a non-secure swipe lockscreen. A secure lock would need a
        # credential we deliberately do not store; require_ready() catches that.
        self.shell("input keyevent KEYCODE_MENU")

    def require_ready(self) -> None:
        """Assert the phone is in a state we agreed to drive. Raises DeviceBlocked."""
        level, charging = self.battery()
        if level < config.MIN_BATTERY_PCT and not charging:
            raise DeviceBlocked(
                f"battery {level}% (<{config.MIN_BATTERY_PCT}%) and not charging"
            )
        self.wake()
        if not self.screen_on():
            raise DeviceBlocked("screen will not wake")

    # -- app control -------------------------------------------------------
    def app_pid(self) -> int | None:
        # `pidof` exits non-zero when nothing matches, which is a normal answer
        # ("not running"), not a failure -- so this bypasses shell()'s rc check.
        cp = _run(["adb", "-s", self.addr, "shell", "pidof", config.PACKAGE], timeout=10)
        out = cp.stdout.strip()
        return int(out.split()[0]) if out else None

    def launch_app(self) -> None:
        self.shell(f"am start -n {config.LAUNCH_ACTIVITY}")

    def force_stop_app(self) -> None:
        self.shell(f"am force-stop {config.PACKAGE}")

    # -- input -------------------------------------------------------------
    def tap_raw(self, x: int, y: int) -> None:
        """Tap in PHYSICAL screen coordinates. Prefer Screen.tap() -- this one
        bypasses the no-tap-zone check and exists for the safety layer itself."""
        self.shell(f"input tap {int(x)} {int(y)}")

    def swipe_raw(self, x1: int, y1: int, x2: int, y2: int, ms: int = 300) -> None:
        self.shell(f"input swipe {int(x1)} {int(y1)} {int(x2)} {int(y2)} {int(ms)}")

    def back(self) -> None:
        self.shell("input keyevent KEYCODE_BACK")

    @staticmethod
    def human_pause() -> None:
        time.sleep(random.uniform(config.MIN_ACTION_DELAY, config.MAX_ACTION_DELAY))
