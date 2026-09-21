"""Per-run structured logging and screenshot retention."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np

from . import config


class RunLog:
    """One run. Writes a JSONL line and keeps its frames for later inspection."""

    def __init__(self, kind: str, dry_run: bool = False) -> None:
        self.kind = kind
        self.dry_run = dry_run
        self.started = time.time()
        self.stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self.dir = config.RUNS / f"{self.stamp}_{kind}"
        self.events: list[dict] = []
        self.data: dict = {}

    def event(self, name: str, **fields) -> None:
        self.events.append({"t": round(time.time() - self.started, 2),
                            "event": name, **fields})

    def shot(self, name: str, frame: np.ndarray) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(self.dir / f"{name}.png"), frame)

    def finish(self, status: str, **fields) -> dict:
        rec = {
            "stamp": self.stamp,
            "kind": self.kind,
            "status": status,
            "dry_run": self.dry_run,
            "duration_s": round(time.time() - self.started, 1),
            **self.data, **fields,
            "events": self.events,
        }
        config.RUNS.mkdir(parents=True, exist_ok=True)
        with config.RUN_LOG.open("a") as fh:
            fh.write(json.dumps(rec) + "\n")
        if self.dir.exists():
            (self.dir / "run.json").write_text(json.dumps(rec, indent=2))
        _prune()
        return rec


def _prune() -> None:
    """Keep only the most recent runs' screenshots; the JSONL stays forever."""
    dirs = sorted((d for d in config.RUNS.iterdir() if d.is_dir()), reverse=True)
    for d in dirs[config.SCREENSHOT_RETENTION_RUNS:]:
        for f in d.iterdir():
            f.unlink()
        d.rmdir()
