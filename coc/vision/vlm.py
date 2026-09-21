"""Tier-3 perception: ask a VLM (OpenRouter) about a frame.

Used where classical CV is brittle or absent: reading a battle result screen,
naming an unknown screen, identifying buildings. It is a FALLBACK, not a
replacement -- template matching and the digit atlas are cheaper, deterministic
and already verified, so they stay first.

Fails closed, per the repo contract: a response that does not parse, or that the
model marks low-confidence, raises rather than returning a guess.
"""

from __future__ import annotations

import base64
import json
import os
import re
import time

import cv2
import numpy as np
import requests

MODEL = "google/gemini-3-flash-preview"
ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
TIMEOUT = 60

# Which gateway `_complete` posts to. DEFAULT IS UNCHANGED ("openrouter"), so every
# existing caller -- `locate.py`, `cli.py`, the tests -- behaves exactly as before
# unless the environment opts in. Set COC_VLM_BACKEND=zen to route the SAME staged
# pipeline through OpenCode Zen instead (`coc/vision/zen.py`, glm-5.3-flash).
#
# Why here and not a new argument: `_complete` is the single place that knows the
# endpoint and the auth header, so swapping it swaps `ask`, `ask_list`,
# `read_battle_result` and all four of locate.py's stages at once, with no change
# to any call site. Measured 2026-09-18: a one-shot whole-frame Zen call found
# 0 of 4 Air Defenses that YOLO had at conf 0.89-0.91, its boxes 100-195 px off
# with the aspect ratio inverted. The staged pipeline is the part that works, so
# the backend is what moves -- never the architecture.
BACKEND = os.environ.get("COC_VLM_BACKEND", "openrouter")
ZEN_MODEL = os.environ.get("COC_ZEN_MODEL", "glm-5.3-flash")
ZEN_PLAN = os.environ.get("COC_ZEN_PLAN", "go")


class VLMError(RuntimeError):
    """The VLM could not be reached, or gave an answer we refuse to trust."""


def _encode(img: np.ndarray, max_w: int = 1100, quality: int = 70) -> str:
    """Downscale + WebP-encode a frame to base64.

    A raw 2392x1080 PNG is ~2.4 MB; at 1100 px wide and q70 WebP it is ~60 KB,
    which is what makes a per-battle call cheap enough to be worth doing.
    """
    if img.shape[1] > max_w:
        s = max_w / img.shape[1]
        img = cv2.resize(img, (max_w, int(img.shape[0] * s)))
    ok, buf = cv2.imencode(".webp", img, [cv2.IMWRITE_WEBP_QUALITY, quality])
    if not ok:
        raise VLMError("failed to encode frame")
    return base64.b64encode(buf.tobytes()).decode()


def _complete(img: np.ndarray, prompt: str, *, max_tokens: int,
              max_w: int = 1100, quality: int = 70,
              model: str | None = None) -> tuple[str, float]:
    """POST one image+prompt; return (raw reply text, latency in seconds).

    Shared by `ask` and `ask_list` so there is exactly one place that knows the
    endpoint, the auth header and the failure mapping. `max_w` is exposed because
    `locate.py` sends tile crops that are already the size it wants them -- passing
    them through the default downscale would throw away the resolution that makes
    per-tile detection work in the first place.
    """
    if BACKEND == "zen":
        from . import zen
        # Zen bills per token and a reasoning model spends the OUTPUT budget
        # thinking: at max_tokens 300 it returns empty or truncated JSON, which
        # looks like a model failure and is not. Floor it.
        txt, dt, _usage = zen.complete(img, prompt, model=model or ZEN_MODEL,
                                       plan=ZEN_PLAN, max_tokens=max(max_tokens, 2000),
                                       max_w=max_w, quality=quality)
        return txt, dt

    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise VLMError("OPENROUTER_API_KEY is not set")
    body = {
        "model": model or MODEL,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url",
             "image_url": {"url": "data:image/webp;base64,"
                                  + _encode(img, max_w=max_w, quality=quality)}},
        ]}],
    }
    t0 = time.time()
    r = requests.post(ENDPOINT, timeout=TIMEOUT,
                      headers={"Authorization": f"Bearer {key}",
                               "Content-Type": "application/json"},
                      data=json.dumps(body))
    if r.status_code != 200:
        raise VLMError(f"HTTP {r.status_code}: {r.text[:200]}")
    return r.json()["choices"][0]["message"]["content"], time.time() - t0


def ask(img: np.ndarray, prompt: str, *, max_tokens: int = 400) -> dict:
    """Ask the VLM about `img`; expects a JSON object back."""
    txt, dt = _complete(img, prompt, max_tokens=max_tokens)
    m = re.search(r"\{.*\}", txt, re.S)
    if not m:
        raise VLMError(f"no JSON in response: {txt[:200]}")
    out = json.loads(m.group(0))
    out["_latency_s"] = round(dt, 2)
    return out


def ask_list(img: np.ndarray, prompt: str, *, max_tokens: int = 1200,
             max_w: int = 1100, quality: int = 70,
             model: str | None = None) -> list:
    """Ask the VLM about `img`; expects a JSON ARRAY back (detections).

    Separate from `ask` because a detector returns a list, and an empty list is a
    legitimate answer ("nothing of these classes in this crop") that must not be
    confused with a parse failure.
    """
    txt, _ = _complete(img, prompt, max_tokens=max_tokens, max_w=max_w,
                       quality=quality, model=model)
    m = re.search(r"\[.*\]", txt, re.S)
    if not m:
        raise VLMError(f"no JSON array in response: {txt[:200]}")
    out = json.loads(m.group(0))
    if not isinstance(out, list):
        raise VLMError(f"expected a JSON array, got {type(out).__name__}")
    return out


RESULT_PROMPT = (
    "This is a Clash of Clans Builder Base battle result screen. Read it exactly. "
    "Reply with ONLY a JSON object: "
    '{"damage_pct": <integer under "Total damage">, '
    '"stars": <number of GOLD/filled stars, 0-3; dark outlined stars do not count>, '
    '"gold": <integer next to the gold icon under Rewards>, '
    '"trophies": <integer next to the hammer icon under Rewards>, '
    '"confident": true|false}. '
    "Set confident=false if this is not a result screen or any field is unreadable."
)


def read_battle_result(frame: np.ndarray) -> dict:
    """Read a battle result screen. Raises unless the model is confident."""
    out = ask(frame, RESULT_PROMPT)
    if not out.get("confident"):
        raise VLMError(f"VLM not confident: {out}")
    for k in ("damage_pct", "stars", "gold"):
        if not isinstance(out.get(k), int):
            raise VLMError(f"field {k!r} missing or not an int: {out}")
    if not 0 <= out["stars"] <= 3:
        raise VLMError(f"implausible star count: {out}")
    return out
