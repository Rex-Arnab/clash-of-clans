# coc/vision/ — perception

Inherits [`../CLAUDE.md`](../CLAUDE.md) and the root [`CLAUDE.md`](../../CLAUDE.md).

## Purpose

Turn a `Frame` into named facts: which screen this is, which loot bubbles are on it, and what the
HUD counters say. This layer reports; it never taps and never decides policy.

## Ownership

| Module         | Owns                                                                                                                                 |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| `templates.py` | masked `matchTemplate`, `HUD_ZONES`, loot-bubble detection + hue classification                                                      |
| `digits.py`    | HUD number reading: segmentation, the glyph atlas, `read_resources`                                                                  |
| `screens.py`   | `Screen` enum, `classify()`, and `ensure_village()` — the navigation panic path                                                      |
| `vlm.py`       | the OpenRouter call itself: encode, POST, `ask` (object) / `ask_list` (array), `read_battle_result`                                  |
| `zen.py`       | the OpenCode Zen / Go call: model→protocol routing, the four vendor SDKs, `complete()`. Reuses `vlm._encode`. Wired into NOTHING yet |
| `locate.py`    | building localisation: stage 0 local detector, then boundary → tiles → detect → NMS → crop verify                                    |
| `yolo.py`      | the local defence detector: ONNX YOLOv5s via `cv2.dnn`, letterbox, NMS, class map, weights sha gate                                  |

## Local contracts

- **The harness never acts on a screen it cannot name.** `classify()` returns `UNKNOWN` and
  `ensure_village()` raises `DeviceBlocked` after `max_steps`. Blind-tapping an unrecognised screen
  is how automation buys gems.
- **Village proof is that the resource counters PARSE, not that they are bright.**
  `_village_hud_present()` runs `read_resources()` and requires >=3 of 4 readable.
  Brightness alone was measured false on 2026-09-08: the League Overview and My
  Army panels leave all four ROIs above the brightness gate while covering the
  village, and the old check called both `HOME_VILLAGE`. Margin is 4/4 village
  vs 0/4 for every panel, so do not "optimise" this back to a pixel statistic.
  **Consequence: `classify()` now depends on `assets/digits/atlas.npz`** via
  `digits.default_atlas()` (process-cached). No atlas, no screen classification.
- **`DISCONNECTED` is the normal first screen, not an edge case.** Runs are an hour apart and CoC
  drops idle sessions, so the "Anyone there? / Reload game" dialog is on the happy path. A reload
  replays the full loading sequence — the 18 s wait is measured, not padding.
- **Matching uses `TM_SQDIFF_NORMED` with an alpha mask — lower is better.** The world animates
  (water, clouds, troop idles, bubble bob); an unmasked crop scores 0.75 on an identical bubble over
  different scenery, indistinguishable from noise. Never drop the mask to "simplify".
- **One masked ring template detects all three bubbles; interior hue names the kind.** Do not add
  per-resource bubble templates.
- **`HUD_ZONES` stays tight.** A previous 300 px-tall left rail silently swallowed a real dark-elixir
  bubble. Widening a zone loses loot with no error — the failure is invisible, so justify any change
  with a frame that shows the false positive it removes.
- **An ambiguous digit raises `UnreadableNumber`; it is never guessed.** Gate is
  `best >= DIGIT_THRESHOLD` **and** `best - runner_up >= 0.05`. A misread digit is a wrong delta that
  looks entirely plausible in the log. `read_resources` maps that to `None` per field, deliberately.
- **Glyphs are scaled aspect-preserving into `GLYPH_BOX` and centred, never stretched.** Stretching
  squashed a narrow `1` by 2.2x and dropped a correct read to 0.750, under the gate.
- **Segmentation is baseline + walk-left-from-the-right-edge, not "every bright blob".** The bars are
  translucent, so the village behind them produces bright speckles inside the ROI.
- **Tesseract is deliberately not used** — closed alphabet, fixed font, fixed density, fixed ROIs.
  Do not reintroduce a document OCR engine.
- **`config.VLM_ENABLED` is `True` and `vlm.py` now exists, but `classify()` still does not read it.**
  The Tier-3 screen-classification fallback (unknown screen → name it → write the answer back as a
  template) is still unbuilt; `vlm.py` currently serves `read_battle_result()` and `locate.py`. Do not
  wire a partial version into `classify()`.
- **Never grade a detector on how many things it found.** Measured 2026-09-12: a single whole-frame
  detection call returned exactly 4 air defenses on 5 different bases — the correct count for these
  town halls — while only 13 of those 20 boxes were on an Air Defense. The model was filling a quota
  from prior knowledge of the game, and the perfect count concealed it. Grade by cropping every box at
  native resolution and looking at it (`locate --overlay`, or `draw()`), never by counting detections.
  A suspiciously stable count is evidence of anchoring as often as of accuracy.
- **`locate` answers `air_defense` / `x_bow` / `inferno_tower` locally by default** (`yolo.py`,
  `detector="hybrid"`). Only classes the detector was never graded on (`town_hall`, `loot_bubble`)
  still go through the VLM stages. Measured 2026-09-17 on the same 9 graded real-phone frames:
  old VLM path 79/89 precise (88.8%), 25.1 s median, 160 calls; hybrid 82/85 (96.5%), 2.7 s, 30
  calls; hybrid `verify=False` 74/75 (98.7%), 0.09 s, 0 calls, lower recall (misses skins).
- **Deploy and spell targets come from `locate.deploy_targets()` — the model ONLY** (owner's
  decision 2026-09-17). It is `verify=False` stage 0: the most precise path measured (74/75), 0.09 s,
  no API call, and it refuses any class the detector was not graded on instead of routing it to the
  VLM. The accepted cost is recall (lava-skin buildings score below the line). Do not "improve"
  targeting by adding the VLM verify back; that trades precision for recall and was declined.
- **`yolo.ACCEPT_CONF = 0.80` is load-bearing.** At or above it 74/75 graded boxes were true;
  below it two thirds were banners, hero cards, the countdown text and UI buttons. Do not lower it
  without re-grading every box, and never return a sub-threshold box unverified.
- **Stage-0 verify CONFIRMS, it never relabels.** A review-band box survives only if the VLM gives it
  the detector's own label. The 7 relabels measured were all wrong (countdown text → air_defense,
  hero cards → x_bow, a real X-Bow → air_defense): handed junk, the verifier picks the nearest
  allowed label. Same-label confirmations are not perfect either (17 true, 2 false over two runs).
- **`yolo.EXPOSED` lists only graded classes.** The network also emits `th` (6/9 precise, never
  saw TH16+ art), `scatter` (0 of 2 found on the live own village) and more — do not add a class to
  `EXPOSED` or `FAST_CLASSES` without crop-grading it at IMGSZ 800 first.
- **The weights are refused unless their sha256 matches.** Every number above belongs to that exact
  export; a re-export (different opset, FP16, CoreML) must be re-graded, not assumed equal.
  CoreML ran 12 ms but moved confidences by up to 0.16 — enough to cross the 0.80 line.
- **`yolo.detect` serialises the forward pass with `_NET_LOCK`; keep it.** The shared `cv2.dnn.Net`
  is not thread-safe: 5 threads started together got each other's boxes (0/5 correct, 5/5 with
  the lock). `test_concurrent_detect_matches_sequential` guards it.
- **The detector is only trustworthy on GREEN sceneries.** On a9's blue underwater scenery its
  Air Defense scores fell below 0.80 (recolouring green bases blue kept 4 of 23 ADs). Model-only
  targeting therefore finds few or no ADs on non-green bases — expected, not a code fault. Live a15
  (dark scenery, 2026-09-17): 2 ADs found on a base that likely had 4; the battle still won 100%.
- **`deploy_targets()` also answers "is this AD still standing?"** in battle (`scratchpad/zaps.py`):
  graded on a10/a11 recorder frames, standing ADs 0.87-0.90, rubble or mid-explosion no box ≥ 0.25 within
  40 px of the aim point (a10, a11). Keep the attack's 40 px radius: ADs 88 px apart are common.

## Work guidance

- Adding a screen state: cut a template (see [`assets/CLAUDE.md`](../../assets/CLAUDE.md)), add the
  enum member, and put the check in `classify()` **cheapest and most specific first**. Record the
  measured true/false-positive margin in the manifest.
- Tuning a threshold without a measured margin from real frames is not a change, it is a guess.
- ROIs and thresholds live in code next to the comment that measured them — do not move them into
  `config.py` unless two modules genuinely need the same value.

## Verification

- `python3 -m pytest tests/ -q` — every labelled sample must still read exactly, and
  `tests/test_yolo.py` must still accept only graded-true buildings (and every clear one).
- Detector / `locate` changes: `python3 -m coc.cli locate --classes air_defense,x_bow,inferno_tower
--overlay /tmp/o.png` on a live grab, then LOOK at every box.
- Detection changes: run `collect --dry-run` on the live phone and read the `detect` events in
  `runs/<stamp>_home_collect/run.json` — quote the per-bubble scores and the first false-positive
  margin, not just the count.

## `zen.py` — OpenCode Zen / Go backend (2026-09-18, MEASURED, not wired in)

An alternative gateway to `vlm.py`'s OpenRouter, added so tier-3 has a second
source. **Nothing imports it**: not `classify()`, not `locate.py`, not `vlm.py`.
It exists to be benchmarked first (`scratchpad/zenbench.py`).

- **Zen and Go are DIFFERENT PRODUCTS on the same key.** Zen (`/zen`) is
  pay-as-you-go and routes each model to its VENDOR'S endpoint — four protocols:
  `/v1/messages` (anthropic SDK), `/v1/responses` (openai), `/v1/models/<id>`
  (google-genai), `/v1/chat/completions` (openai-compatible). Go (`/zen/go/v1`)
  is a $10/mo subscription, one OpenAI-compatible endpoint, its own catalogue and
  its own prices. `plan=` is an explicit argument; ids overlap between them.
- **The model id does NOT predict the protocol.** `qwen3.5-plus` is served over
  Anthropic's `/v1/messages`. `family()` matches explicit id sets transcribed from
  the docs table and RAISES on anything absent — never a prefix rule.
- **Go requires `x-opencode-session` and a non-generic User-Agent**, else 400
  `MissingSessionID`. Its docs scope it to coding-agent traffic; the owner chose
  it for this workload on 2026-09-18 with that stated.
- **`max_tokens` is load-bearing on reasoning models.** At 300, `mimo-v2.5` scored
  6/13 and `deepseek-v4-flash-vision-exp` 8/13 with truncated JSON and empty
  completions — all of it the CAP, not the model. At 2000 the same models went
  13/13 and 12/13 with zero errors. Never grade a model at a budget it spent
  thinking. `complete()` raises on an empty completion so this is loud, not silent.
- **`deepseek-v4-flash-vision-exp` is ~10x faster on Go than on OpenRouter**:
  2.54-2.95 s median here against the 19-54 s that got it rejected on 2026-09-10.
  A model's verdict does not transfer between gateways.

### Measured on stored Builder Base frames (`scratchpad/zenbench.py`, Go plan)

RESULT = stars + damage off 13 `r0_result` frames, truth from the b2-b14 table.
SCREEN = 4 classes over 68 frames. `$/1k` is from the gateway's own usage counts.

| model | RESULT stars/dmg | SCREEN | p50 | $/1k frames | errors |
|---|---|---|---|---|---|
| **`glm-5.3-flash`** | **13/13 · 13/13** | **68/68** | **2.86-3.00 s** | **0.134-0.146** | 0 |
| `omen-alpha` | 13/13 · 13/13 | 68/68 | 2.71-3.40 s | 0.188-0.216 | 0 |
| `qwen3.8-flash` | 13/13 · 13/13 | 68/68 | 3.87-5.25 s | 0.156-0.211 | 0 |
| `minimax-m3` | 13/13 · 13/13 | 67/68 | 2.82-4.20 s | 0.437-0.451 | 0 |
| `mimo-v2.5` | 13/13 · 13/13 | — | 8.22 s | 0.193 | 0 |
| `deepseek-v4-flash-vision-exp` | 12/13 · 13/13 | 66/68 | 2.54-2.95 s | 0.129-0.225 | 1 empty |

Unavailable on this account: `gpt-5.6-luna` (500 on all 13), `qwen3.5-plus`
("Model is unavailable"), `muse-spark-*-contributor` (403, needs a data-collection
opt-in), `ox-alpha-free` ("not supported").

- **A shared wrong answer means a bad LABEL, not a bad model.** `glm-5.3-flash`
  and `omen-alpha` independently called `b2_20260918/p0_entry` a
  `start_attack_dialog` against a stem that said `own_village`. Looking at the
  frame, b2's runner grabbed it after the panel opened: **the models were right**
  and the score was 67/68 only because of the label. `zenbench.LABEL_OVERRIDE`
  records the correction. Grade by looking, exactly as with the detector boxes.
- **`p0_entry` and `r1_after_return` are ONE class** (`own_village`) in the bench:
  same screen, same HUD, differing only in the star counter and gold. Splitting
  them would measure clairvoyance, not perception.
- These numbers say the model READS a settled screen. They say nothing about
  aiming: the 2026-09-10 finding (3 of 30 deploy points on legal ground, median
  miss 29 px) stands, and `deploy_targets()` remains model-only local YOLO.

## `vlm.py` — Tier-3 fallback (OpenRouter, `google/gemini-3-flash-preview`)

For what classical CV cannot do: reading a result screen, naming an unknown
screen, locating buildings. It is a FALLBACK — template matching and the digit
atlas are cheaper, deterministic and already verified, so they stay first.

- **Fails closed.** A response that does not parse, or that the model flags as
  not confident, raises `VLMError` rather than returning a guess.
- Frames are downscaled to 1100 px and WebP-encoded: **42 KB vs ~2.4 MB raw**,
  which is what makes a per-battle call affordable.
- **`read_battle_result()` is VALIDATED: 4/4 exact** on known result screens
  (damage %, stars, gold), ~3 s per call.
- **Building localisation lives in `locate.py`.** Its VLM path measured 100% precision (18/18),
  90% recall on `air_defense` over 5 frames on 2026-09-12 — but on 9 different frames on 2026-09-17
  it was 30/34 (two X-Bows and a storage called Air Defense), x_bow 23/26, inferno 26/29. Treat the
  18/18 as a small-sample high. `town_hall` accuracy is still UNMEASURED; do not route deploys off it.
- **`locate`'s `loot_bubble` is measured WRONG — use `templates.py` instead.** On the live frame it
  boxed the four small resource droplets and missed every large pink dome, the opposite of its class
  description. The masked-ring template detector already in `templates.py` is verified for bubbles
  and is cheaper; the VLM has no business doing this one.
- **One whole-frame call is not a detector.** `locate.py` splits the question into stages precisely
  because the one-shot version scored 65% precision / 65% recall on the same frames. The per-crop
  verify stage is what lifts 86% → 100%: at native zoom the model separates an X-Bow (tan base,
  horizontal crossbow limbs) from an Air Defense (purple platform, vertical red-tipped tubes)
  perfectly, having confused them at full-frame scale. Do not "simplify" locate back to one call.
- Latency ~6 s for a 14-building query, which fits inside the 54 s battle prep
  window — that is what makes VLM-guided aiming feasible at all.
