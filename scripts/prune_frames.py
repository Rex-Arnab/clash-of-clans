"""Drop the screenshots of old farm runs; keep every log and JSON record.

    python3 scripts/prune_frames.py              # dry run: what would go, and how many bytes
    python3 scripts/prune_frames.py --apply      # delete it
    python3 scripts/prune_frames.py --keep 10    # keep the 10 newest runs whole (default 5)

The same retention idea as `coc/report.py:_prune`, for `scratchpad/farm/`, which had no bound:
2.5 GB on 2026-10-06, mostly full-size Builder Base PNGs at 2-4 MB each. Only images go;
`rec.json`, `farm.jsonl`, `console.log` and every other record stay.

Two things are never touched, because the regression gates read them:
  - a run folder whose name appears in any `test_*.py` / `replay_*.py` / `tests/` file;
  - `view_mid.jpg` anywhere -- test_bar, test_cards and test_freeze glob it across every run.
`scratchpad/battles/` and `scratchpad/bb/battles/` are not pruned: they are the battle corpora.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FARM = ROOT / "scratchpad" / "farm"
IMAGES = {".png", ".jpg", ".jpeg", ".webp"}
KEEP_NAMES = {"view_mid.jpg"}


def referenced() -> tuple[set[str], set[str]]:
    """Run folder names the tests and replays open by name, and the prefixes they glob
    (`farm/learn_*/...` in test_optimization -- missing it cost 1118 learn-mode frames)."""
    names: set[str] = set()
    prefixes: set[str] = set()
    sources = [*ROOT.glob("scratchpad/**/test_*.py"), *ROOT.glob("scratchpad/**/replay_*.py"),
               *ROOT.glob("tests/*.py")]
    for src in sources:
        for name, star in re.findall(r"farm/([A-Za-z0-9_.-]*)(\*?)", src.read_text(errors="ignore")):
            if star and name:
                prefixes.add(name)
            elif name:
                names.add(name)
    return names, prefixes


def doomed(keep: int) -> list[Path]:
    runs = sorted((d for d in FARM.iterdir() if d.is_dir()),
                  key=lambda d: d.stat().st_mtime, reverse=True)
    names, prefixes = referenced()
    out = []
    for d in runs[keep:]:
        if d.name in names or d.name.startswith(tuple(prefixes)):
            continue
        out += [f for f in d.rglob("*") if f.is_file() and f.suffix.lower() in IMAGES
                and f.name not in KEEP_NAMES]
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", type=int, default=5, help="newest runs kept whole")
    ap.add_argument("--apply", action="store_true", help="delete; without it, only report")
    args = ap.parse_args()
    files = doomed(args.keep)
    size = sum(f.stat().st_size for f in files)
    verb = "deleted" if args.apply else "would delete"
    if args.apply:
        for f in files:
            f.unlink()
    print(f"prune_frames: {verb} {len(files)} images, {size / 1e6:.0f} MB, "
          f"from {FARM.relative_to(ROOT)} (newest {args.keep} runs kept whole)")


if __name__ == "__main__":
    main()
