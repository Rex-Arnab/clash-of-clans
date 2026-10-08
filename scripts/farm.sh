#!/bin/bash
# Launcher for the farming supervisor (scratchpad/farm.py).
#
#   scripts/farm.sh                       menu: mode, priority, plan, battles, start / dry run
#   scripts/farm.sh gold --max-cycles 3   no menu: shortcut word + farm.py options
#   scripts/farm.sh -h
#
# What it checks and refuses is in scratchpad/farmmenu.py. PATH and PYTHON are absolute for the
# same reason as run_collect.sh: adb is not on a non-login PATH, and every run would otherwise
# fail at device discovery. exec, so Ctrl-C and the exit code belong to farm.py itself.
set -uo pipefail
export PATH="/opt/homebrew/share/android-commandlinetools/platform-tools:/opt/homebrew/bin:$PATH"
PYTHON="/Users/arnabbiswas/.pyenv/versions/3.13.2/bin/python3"
cd "$(dirname "$0")/.." || exit 1
# scratchpad/farm/ grew to 2.5 GB of screenshots; keep the newest runs' images only.
"$PYTHON" scripts/prune_frames.py --apply || echo "prune_frames failed; farming anyway" >&2
exec "$PYTHON" scratchpad/farmmenu.py "$@"
