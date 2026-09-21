"""OpenCode Zen backend for tier-3 perception — an alternative to `vlm.py`'s OpenRouter.

Zen (https://opencode.ai/docs/zen) is an AI gateway: one key, `OPENCODE_API_KEY`,
in front of 103 models. It does NOT serve one uniform API. It routes each model to
its VENDOR'S OWN endpoint, so this module speaks four protocols and picks by model
id. The mapping is copied from the endpoint table in the Zen docs on 2026-09-18 —
it is NOT derived from the id prefix, because the prefix lies: `qwen3.5-plus` and
`qwen3.6-plus` are served over Anthropic's /v1/messages, not OpenAI's.

Every call goes through the vendor's official SDK (`anthropic`, `openai`,
`google-genai`), never a hand-rolled shim, which is also what the repo owner
requires of any vendor integration.

This module is ADDITIVE. It does not import into `vlm.py`, `locate.py` or
`classify()`, and nothing in either base calls it yet. It exists so the model
bake-off (`scratchpad/zenbench.py`) can measure candidates against stored frames
BEFORE any of them is trusted with a live decision. Wiring the winner into the
perception path is a separate, measured change.

Fails closed like the rest of the layer: an unknown model id, a missing key, a
non-200, or an empty completion raises `VLMError` rather than returning a guess.
"""

from __future__ import annotations

import os
import time
import uuid

import numpy as np

from .vlm import VLMError, _encode

API_BASE = "https://opencode.ai/zen"
GO_BASE = "https://opencode.ai/zen/go/v1"
TIMEOUT = 120.0

# --- model -> protocol, transcribed from https://opencode.ai/docs/zen endpoint table.
# Only ids that appear in that table are reachable over the API; several models the
# TUI offers (qwen3.6-plus-free, kimi-k2.5-free, minimax-m3-free, x-preview-f-free)
# are absent from it and are therefore refused here rather than guessed at.
_ANTHROPIC = {
    "claude-fable-5-1", "claude-fable-5", "claude-opus-5", "claude-opus-4-8",
    "claude-opus-4-7", "claude-opus-4-6", "claude-opus-4-5", "claude-sonnet-5",
    "claude-sonnet-4-6", "claude-sonnet-4-5", "claude-haiku-4-5",
    "qwen3.7-max", "qwen3.7-plus", "qwen3.6-plus", "qwen3.5-plus",
}
_GOOGLE = {
    "gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash",
    "gemini-3.5-flash-lite", "gemini-3.1-pro", "gemini-3-flash",
}
_RESPONSES = {
    "gpt-6-astra", "gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna", "gpt-5.5",
    "gpt-5.5-pro", "gpt-5.4", "gpt-5.4-pro", "gpt-5.4-mini", "gpt-5.4-nano",
    "gpt-5.3-codex", "gpt-5.3-codex-spark", "gpt-5.2", "gpt-5.2-codex", "gpt-5.1",
    "gpt-5.1-codex", "gpt-5.1-codex-max", "gpt-5.1-codex-mini", "gpt-5", "gpt-5-codex",
    "gpt-5-nano", "grok-4.6", "grok-4.5", "grok-build-0.1", "muse-spark-1.3",
    "muse-spark-1.2", "muse-spark-1.3-contributor-free",
}
_CHAT = {
    "deepseek-v4-pro", "deepseek-v4-flash", "deepseek-v4-flash-vision-exp",
    "minimax-m3", "minimax-m2.7", "minimax-m2.5", "glm-5.3-flash", "glm-5.3",
    "glm-5.2", "glm-5.1", "glm-5", "kimi-k2.5", "kimi-k2.6", "kimi-k2.7-code",
    "kimi-k3", "big-pickle", "mimo-v2.5-free", "ling-3.0-flash-fin-free",
    "nemotron-3-ultra-free", "nemotron-3.5-lightning-free",
}


# OpenCode GO is a SEPARATE product from Zen, not a subset: a subscription plan
# served from one OpenAI-compatible endpoint, with its own catalogue and its own
# prices. Roughly half these ids also exist under Zen AT A DIFFERENT PRICE
# (`glm-5.3-flash` out is 0.50 on Zen, 0.50 on Go; `deepseek-v4-flash-vision-exp`
# out is 0.28 on Zen, 0.60 on Go), so the plan is an explicit argument and is never
# inferred from the model id. Ids from models.dev, fetched 2026-09-18.
_GO = {
    "deepseek-v4-flash", "deepseek-v4-flash-vision-exp", "deepseek-v4-pro",
    "deepseek-v4.1-flash", "glm-5", "glm-5.1", "glm-5.2", "glm-5.3", "glm-5.3-flash",
    "gpt-5.6-luna", "grok-4.5", "grok-4.6", "hy3", "hy4-preview", "kimi-k2.5",
    "kimi-k2.6", "kimi-k2.7-code", "kimi-k3", "longcat-2.0", "mimo-v2-omni",
    "mimo-v2-pro", "mimo-v2.5", "mimo-v2.5-pro", "minimax-m2.5", "minimax-m2.7",
    "minimax-m3", "muse-spark-1.2-contributor", "muse-spark-1.3-contributor",
    "omen-alpha", "ox-alpha-free", "qwen3.5-plus", "qwen3.6-plus", "qwen3.7-max",
    "qwen3.7-plus", "qwen3.8-flash", "qwen3.8-max",
}


def family(model: str, plan: str = "zen") -> str:
    """Which protocol serves `model` under `plan`. Raises rather than guessing.

    `plan="go"` is one OpenAI-compatible endpoint for everything, so the answer is
    always "go"; `plan="zen"` has to pick among four vendor protocols.
    """
    if plan == "go":
        if model in _GO:
            return "go"
        raise VLMError(f"{model!r} is not in the OpenCode Go catalogue")
    for name, ids in (("anthropic", _ANTHROPIC), ("google", _GOOGLE),
                      ("responses", _RESPONSES), ("chat", _CHAT)):
        if model in ids:
            return name
    raise VLMError(f"{model!r} is not in the Zen endpoint table; refusing to guess "
                   f"its protocol")


def _key() -> str:
    k = os.environ.get("OPENCODE_API_KEY")
    if not k:
        raise VLMError("OPENCODE_API_KEY is not set")
    return k


def complete(img: np.ndarray, prompt: str, *, model: str, max_tokens: int = 400,
             max_w: int = 1100, quality: int = 70,
             plan: str = "zen") -> tuple[str, float, dict]:
    """POST one image+prompt to Zen. Returns (reply text, latency s, usage dict).

    Signature mirrors `vlm._complete` (which returns just text+latency) plus the
    token usage, because the whole point of the bake-off is cost per frame and the
    gateway is the only place that knows the real image-token count.

    Frames are WebP-encoded at 1100 px by `vlm._encode` — 42 KB against ~2.4 MB
    raw — and every one of the four protocols accepts image/webp, so the existing
    encoding advantage carries over unchanged.
    """
    b64 = _encode(img, max_w=max_w, quality=quality)
    fam = family(model, plan)
    t0 = time.time()
    text, usage = _DISPATCH[fam](b64, prompt, model, max_tokens)
    dt = time.time() - t0
    if not text or not text.strip():
        raise VLMError(f"{model} returned an empty completion "
                       f"(usage={usage}); reasoning may have consumed the budget")
    return text, dt, usage


def _via_anthropic(b64: str, prompt: str, model: str, max_tokens: int):
    from anthropic import Anthropic
    # base_url is the /zen root: the SDK appends its own "/v1/messages".
    c = Anthropic(api_key=_key(), base_url=API_BASE, timeout=TIMEOUT, max_retries=1)
    r = c.messages.create(
        model=model, max_tokens=max_tokens,
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64",
                                         "media_type": "image/webp", "data": b64}},
            {"type": "text", "text": prompt},
        ]}],
    )
    text = "".join(b.text for b in r.content if getattr(b, "type", "") == "text")
    u = getattr(r, "usage", None)
    return text, {"in": getattr(u, "input_tokens", 0), "out": getattr(u, "output_tokens", 0)}


def _via_responses(b64: str, prompt: str, model: str, max_tokens: int):
    from openai import OpenAI
    c = OpenAI(api_key=_key(), base_url=f"{API_BASE}/v1", timeout=TIMEOUT, max_retries=1)
    kw = {}
    if model.startswith("gpt-5"):
        # The 2026-09-10 OpenRouter sweep rejected gpt-5-nano/gpt-5-mini because
        # "reasoning consumes the whole token budget, empty content". On the
        # Responses API that is controllable, so pin it low and re-measure rather
        # than inherit the verdict from a different gateway.
        kw["reasoning"] = {"effort": "low"}
    r = c.responses.create(
        model=model, max_output_tokens=max(max_tokens, 2000), **kw,
        input=[{"role": "user", "content": [
            {"type": "input_text", "text": prompt},
            {"type": "input_image", "image_url": f"data:image/webp;base64,{b64}"},
        ]}],
    )
    u = getattr(r, "usage", None)
    return (getattr(r, "output_text", "") or "",
            {"in": getattr(u, "input_tokens", 0), "out": getattr(u, "output_tokens", 0)})


# One stable id for the life of the process. The Go endpoint rejects a request
# without `x-opencode-session` ("cannot be routed efficiently"), and its docs also
# ask for a user agent that is not a generic SDK name, so both are set explicitly.
GO_SESSION = f"coc-vision-{uuid.uuid4().hex[:20]}"
GO_HEADERS = {"x-opencode-session": GO_SESSION, "User-Agent": "coc-vision-bench/1.0"}


def _via_go(b64: str, prompt: str, model: str, max_tokens: int):
    """OpenCode Go: one OpenAI-compatible endpoint for the whole catalogue."""
    return _chat_at(GO_BASE, b64, prompt, model, max_tokens, headers=GO_HEADERS)


def _via_chat(b64: str, prompt: str, model: str, max_tokens: int):
    return _chat_at(f"{API_BASE}/v1", b64, prompt, model, max_tokens)


def _chat_at(base: str, b64: str, prompt: str, model: str, max_tokens: int,
             headers: dict | None = None):
    from openai import OpenAI
    c = OpenAI(api_key=_key(), base_url=base, timeout=TIMEOUT, max_retries=1,
               default_headers=headers)
    r = c.chat.completions.create(
        model=model, max_tokens=max_tokens,
        messages=[{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url",
             "image_url": {"url": f"data:image/webp;base64,{b64}"}},
        ]}],
    )
    u = getattr(r, "usage", None)
    return (r.choices[0].message.content or "",
            {"in": getattr(u, "prompt_tokens", 0), "out": getattr(u, "completion_tokens", 0)})


def _via_google(b64: str, prompt: str, model: str, max_tokens: int):
    import base64 as _b64
    from google import genai
    from google.genai import types
    # Zen serves Gemini at /zen/v1/models/<id>, which is the shape the SDK builds
    # from base_url + api_version. Auth header is the one uncertainty in this
    # module: Zen issues a bearer token, Google's SDK sends x-goog-api-key, so
    # both are set and the live probe in zenbench.py is what settles it.
    c = genai.Client(api_key=_key(), http_options=types.HttpOptions(
        base_url=API_BASE, api_version="v1",
        headers={"Authorization": f"Bearer {_key()}"}, timeout=int(TIMEOUT * 1000)))
    r = c.models.generate_content(
        model=model,
        contents=[types.Part.from_bytes(data=_b64.b64decode(b64), mime_type="image/webp"),
                  prompt],
        config=types.GenerateContentConfig(max_output_tokens=max(max_tokens, 2000)),
    )
    u = getattr(r, "usage_metadata", None)
    return (r.text or "", {"in": getattr(u, "prompt_token_count", 0),
                           "out": getattr(u, "candidates_token_count", 0)})


_DISPATCH = {"anthropic": _via_anthropic, "responses": _via_responses,
             "chat": _via_chat, "google": _via_google, "go": _via_go}
