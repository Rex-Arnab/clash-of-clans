#!/bin/bash
# Scheduler entry point.
#
# launchd does not source ~/.zshrc, so PATH and any credentials have to be set
# here explicitly. adb in particular is not on the default launchd PATH, and
# without it every run fails at device discovery.
set -uo pipefail

export PATH="/opt/homebrew/share/android-commandlinetools/platform-tools:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"
PROJECT="/Users/arnabbiswas/Documents/personal/experiment/clash-of-clans"
PYTHON="/Users/arnabbiswas/.pyenv/versions/3.13.2/bin/python3"

# OPENROUTER_API_KEY lives in the interactive shell profile; pull it from there
# for the Tier-3 vision fallback. Absent is fine -- that path is optional.
if [ -z "${OPENROUTER_API_KEY:-}" ] && [ -f "$HOME/.zshrc" ]; then
  OPENROUTER_API_KEY="$(/bin/zsh -lc 'printf %s "${OPENROUTER_API_KEY:-}"' 2>/dev/null)"
  export OPENROUTER_API_KEY
fi

cd "$PROJECT" || exit 1
# Spread the start across the hour rather than firing exactly on the minute.
exec "$PYTHON" -m coc.cli collect --jitter 420
