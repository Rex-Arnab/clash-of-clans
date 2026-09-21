# Clash of Clans automation — TODO

## HOME VILLAGE: PRIMARY SEARCH SURFING VERIFIED (2026-09-20)

The search flow had been reading Gold and Elixir but immediately attacking because it treated the
purple deployment-overlay detector (`prep_active`) as a scout-screen condition. On three native
scouting frames it was false (4.45–6.06% purple versus its 15% threshold) while the orange Next
button and battle screen were both present. `loot.search` now uses the Next button as the scouting
contract; `_next_base` requires that button to disappear into clouds and reappear on a battle screen
before it accepts a new candidate.

**Live Home Village, phone `EQEMVG6HSOUO9DT4`, c190942:** primary search rejected **five** bases,
with observed cloud transitions of **3.2–3.4 s**, then selected the sixth only because Elixir was
**1,402,822** (threshold 900,000). Its five rejected Gold/Elixir pairs were
722,381/722,999; 160,002/422,885; 415,540/832,889; 257,045/259,876; and 696,733/481,955.
Supervisor and child agreed on **+867,542 Gold / +1,662,822 Elixir / +15,427 Dark**.

**Gates:** the focused search suite passed **4/4**:
`PYTHONPATH=.. python3 -m pytest test_battle_clock.py -q -k 'live_scouting or
poor_bases_are_skipped or search_attacks_after_max_nexts or unreadable_loot'`.

## HOME VILLAGE: GOLD REWARD PICKUP VERIFIED (2026-09-20)

The reward picker now preserves native popup frames at ribbon detection plus 0.4 s, 1.2 s, and
2.0 s. It journals the raw Gold, Elixir, and Dark label scores for every retained frame, so a
card that is still animating is evidence, never a guessed tap. A 1196px review-image Gold crop
was removed; the replacement is a native 2392px crop from c174926's fully shown 1,615,406-Gold
card. Gold ranks ahead of Elixir and Dark whenever its label clears the same 0.85 safety bound.

**Live Home Village, phone `EQEMVG6HSOUO9DT4`, c175658:** two full Gold offers were captured and
picked, at **(1605, 555)** and **(1221, 555)**. The runner recorded **15/15 dragons confirmed**;
the independent supervisor and child reads agreed on **+959,777 Gold / +535,970 Elixir / +3,480
Dark** (`scratchpad/farm/gold-verify-20260920/farm.jsonl`). Native evidence is
`scratchpad/farm/gold-verify-20260920/home_village/c175658/reward_popup_*`.

**Measurements / gates:** the verified Gold source scored **1.000** and a Dark source scored
**0.489** for Gold, so no Dark misclassification. `PYTHONPATH=.. python3 -m pytest
test_battle_clock.py -q` passed **86/86**. The account's current Archer Queen and archived Grand
Warden signatures both resolve to `hero_a` at x=916, retaining the historical replay gate without
changing the live slot.

## HOME VILLAGE: POST-BATTLE READS + PRIMARY LOOT POLICY VERIFIED (2026-09-20)

`farm.py` no longer treats a child `rc=0` as a measured supervisor success when the post-battle HUD
cannot be read. It now logs the initial miss, uses the normal interlocked recovery ladder once, and
re-reads after settling; a second miss is `measured: false` and contributes to the failure limit.
It never turns unreadable counters into zero deltas. Historical measurement:
`jq -s '[.[] | select(.what == "battle_end" and .rc == 0)] ...' scratchpad/farm/run1/farm.jsonl`
found **19/79** missing supervisor readings, with **16** valid child readings underneath them.

The owner changed the resource policy: `primary` means **Gold or Elixir first**. `loot.search`
uses up to eight Nexts for either threshold (gold >= 800,000 or elixir >= 900,000), then lets Dark
Elixir (>= 7,000) be a fallback over the final two choices; the final candidate remains bounded and
is accepted. `farm.is_done(..., "primary")` watches Gold/Elixir only, never Dark.

**Live Home Village, phone `EQEMVG6HSOUO9DT4`, 2026-09-20:** `farm.py ... --priority gold
--max-cycles 1` completed c132857 with `measured: true`; supervisor and child agreed on
**+2,838,271 gold / +2,878,683 elixir / +26,088 dark**. Visual frames show all **15/15 dragons**
and **11/11 Lightning** expended, then a **100% three-star** result screen. `attack7.py` now writes
`dragons_confirmed` / `dragons_requested`; c132857 recorded **15/15**.

**Gates:** targeted primary-policy + replay tests **13 passed**; primary-phone dry-run identified
HOME_VILLAGE at 28% battery and logged `would_run` without a battle.

## HOME VILLAGE + SUPERVISOR: THE FARM RUN NOW ASKS WHAT IT IS FARMING FOR (2026-09-19)

The owner's report: "I don't want dark elixir right now, but it's finding bases which have highest
dark elixir." Two hardcoded 2026-09-17 goals caused it -- `loot.DARK_MIN` picked every base for its
Dark Elixir, and `farm.is_done` halted on whichever storage filled first.

`farm.py` now asks ONCE at startup (`--priority gold|elixir|dark` skips the question; **no tty =
refuse, exit 2**, so a scheduled run never waits on an answer nobody will type). The answer drives:

- **the 90% stop rule** -- `farm.is_done(res, caps, priority)` watches THAT resource only;
- **the Home Village base search** -- exported as `FARM_PRIORITY`, read by `loot.priority()`, which
  picks `loot.MINS[priority]` as the Next-past threshold.

Builder Base has no dark storage: a dark run there reverts to the old any-resource rule and says so
in the halt reason (owner's choice over halting).

**Perception added** (`hud.loot_amount`, Home Village): gold `(172,136,470,192)` and elixir
`(172,194,470,250)` are the dark box shifted up one 58 px row pitch. On the 24 stored scouting
frames `battles/a*/frames/t0000*.jpg`: **21/24 read all three rows, 3 refused** (`UnreadableNumber`
-- never a wrong number). Graded by eye on a13/a25/a29/a30: **12/12 exact**. `hud.loot_dark` kept as
a name because `replay_a10.py` patches it.

| priority | threshold         | of the 24 stored bases        | rationale                                                                |
| -------- | ----------------- | ----------------------------- | ------------------------------------------------------------------------ |
| gold     | 800,000           | attack 9 (38%), Next past 15  | DARK_MIN's own ~37% design point; range 70,271-1,662,834, median 675,002 |
| elixir   | 900,000           | attack 10 (42%), Next past 14 | range 215,675-1,843,338, median 673,588                                  |
| dark     | 7,000 (unchanged) | attack 18 (75%)               | biased: these bases had already passed the dark filter                   |

**Gates.** `scratchpad/`: 123 passed (was 123 -- unchanged) + **17 new tests**, all of which FAIL
against a reconstructed pre-change copy of hud/loot/farm (17 failed) and pass against the new code.
`tests/`: 15 passed.

**Live, phone `EQEMVG6HSOUO9DT4`, Home Village, `farm.py --dry-run`:** no-tty run exited 2 with the
message; a pty run rejected "trophies", accepted "g" -> gold, and printed
`*gold 10,003,918 (43.5%)  elixir 6,176,027 (28.1%)  dark 263,046 (67.4%)` -- dark at 67.4% no
longer competes for the halt, and the run proceeded to `would_run attack7.py`.

- [ ] **Not yet verified in a live battle**: no attack has run with `FARM_PRIORITY=gold`, so the
      gold thresholds are offline numbers on a biased sample. First live gold run should be read
      back from `farm.jsonl` (`search_start`, `base res=gold have=... need=800000`).
- [ ] The reward popup still always picks Dark Elixir. Making it follow the priority needs gold and
      elixir card templates cut from a live "Pick a Reward!" popup; only `reward_dark_{mid,end}.png`
      exist. Capture them during the next battles.

Device: Realme RMX5033 (serial `EQEMVG6HSOUO9DT4`), Android 16, wireless adb.
Game: `com.supercell.clashofclans` 18.600.1, landscape 2392x1080, density 360.

## BUILDER BASE TARGET MET BY THE SUPERVISOR (2026-09-19)

`farm.py` farmed the Builder Base to its stop condition unattended and halted itself:

    [halt] builder_base done (elixir 5,230,560 >= 90% of 5,500,000); switching is off

Elixir **4.4% -> 95.1%** of the 5,500,000 cap over the session; gold 239,380 -> 1,039,380 (18.9%).
Most of the elixir came from the 9-star track (255,000 gold + 255,000 elixir per payout), not from
per-battle rewards, which remain **0 elixir**.

### TWO CORRECTIONS TO THE 2026-09-18 ANALYSIS. Both matter.

1. **Damage % is NOT comparable between battles, so the `min_sep` vs damage correlation is partly
   invalid.** A Builder Base 2.0 battle that reaches stage 2 reports the SUM across both stages:
   measured today at **145%** and **200%** on real result screens. Mixing one- and two-stage battles
   in one damage column compares different quantities. **Use STARS or GOLD.** (The 145% was also my
   own false alarm: I called it an impossible misread, then opened the frame and the screen really
   does say 145%. `glm-5.3-flash` was right.)
2. **The A/B, at n=5, points the OTHER WAY.** arm 150 (tight): n=3, mean 1.67 stars. arm 600 (wide):
   n=2, mean **2.50** stars — including a 3-star 200% run at sep 220.3. This is exactly what "needs
   ~27 battles per arm" means: the n=17 hint (tight is better) is not supported by the first five
   controlled battles, and neither result should be acted on yet.

### The A/B knob itself works

`bbspots.SEP_CAP`, from `BB_SEP_CAP`, caps where both planners START their largest-first separation
search. **Default 600 is exactly the old behaviour** — verified on a stored prep frame: `None`/`600`
both give min_sep 260.1/arc 54, `150` gives 153.3/arc 36. `attack1.py` needed no edit. `farm.py
--ab-sep 150,600` alternates per battle and every row self-labels.

### RECOVERY BUG FOUND AND FIXED — it cost a run

A run halted "lost the village" after six `recover_wait` steps. The phone was sitting on the 9-star
track's **"Star Bonus!" modal** (255,000 gold + 255,000 elixir, one green Okay). It dims the HUD, so
the digits will not parse and `which_base` correctly answered UNKNOWN — but `recover()` had **no
popup-dismiss rung at all**, which the plan had specified and the implementation omitted.

Fixed: the ladder now dismisses a modal, preferring the **red X** whenever one exists, because a
green centre button WITH a red X is the Start Attack panel and the green one is "Find Now!" — that
tap starts a battle instead of closing anything. A lone green button is treated as Okay.
**`builder_base.modal_present()` returns False on this modal** (it keys on the brown panel; this one
is blue), so the dismiss must NOT be gated on it. Verified live against the stuck phone: dismissed
at (1198,857), recovered to BUILDER_BASE, and the bonus landed (+255,000 each).

Also fixed: `farmlib.startup()` now retries a `DeviceError` (3 attempts). A transient
`dumpsys power` failure ("Broken pipe while dumping service") killed a batch at startup while an
immediate reconnect was fine; `adb devices` lists TWO transports to this phone. `DeviceBlocked` is
never retried.

Gates after all of it: `tests/` 15 passed; `scratchpad/bb/test_bb.py` 63 passed / 12 skipped.

- [ ] The A/B needs ~27 battles per arm on STARS or GOLD, not damage %. n=5 so far.
- [ ] Builder Base is at 95.1% elixir / 18.9% gold. Further Builder Base runs now halt immediately
      on the elixir rule; a gold-only target would be needed to keep farming there.

## BUILDER BASE ATTACK QUALITY — INVESTIGATED (2026-09-19)

Builder Base. Prompted by two supervised 1-star runs (+30,000 gold each) and the question "what is
happening in the battle and how do we improve it".

### FIRST: two things that LOOK like bugs and are NOT. Do not "fix" them.

- **7 slots plan only 6 unique points, and that is deliberate.** `deploy_pass` plans `n = len(troops)`
  = 6 points for the 6 dragons, then puts the HERO on the middle one: "r6 put it alone on its own
  flank: dead at T+56, run over at 63%. In r5 it shared the dragons' flank, survived, and carried the
  run from 72% to 100%." The duplicate coordinate in every `plan` event is the hero sharing a dragon's
  spot, by design.
- **The 3 ability passes at T+10/18/26 re-fire the same slots, and that is deliberate too** (added at
  b6 so a late-deploying unit still gets its ability). The in-game "You need to wait before using the
  hero ability again!" is the game refusing a duplicate — wasted taps, not a malfunction.

### Result reading is now AUTOMATIC, and validated 12/12

`farm.read_result()` reads stars + damage off `frames/r0_result.png` with `glm-5.3-flash` via
`coc/vision/zen.py`. **Agreed with the hand-read b1-b14 table on 12 of 12 battles it was confident
about** (b1 has no result frame; b6 it declined). ~3 s and ~$0.0001 a battle, optional — no
`OPENCODE_API_KEY` means no label, never a failed battle. `farm.plan_params()` pulls `min_sep` /
`arc_deg` from the child's own plan event, so **every battle from now on is a labelled
(parameters -> outcome) row** in `farm.jsonl`. Until now nothing machine-recorded the outcome and
the b1-b14 damage figures existed only because a human transcribed them.

### The analysis — n=17, and it does NOT support a parameter claim

`scratchpad/bb_dataset.json` (14 historical + 3 supervised).

|                     | value                               |
| ------------------- | ----------------------------------- |
| damage mean / sd    | **58.0 / 21.2**                     |
| `min_sep` vs damage | pearson **-0.367**, spearman -0.213 |
| `arc_deg` vs damage | pearson -0.086, spearman -0.174     |
| sep < 210 (n=6)     | mean **68.2**, sd 23.6              |
| sep >= 210 (n=11)   | mean **52.5**, sd 17.5              |

There is a HINT that tighter separation helps — the two 100% runs sit at 135.2 and 197.6 — and the
sign is consistent across both correlation measures. **It is not confirmable at n=17.** The observed
gap is 15.7 points against a pooled sd of 20.8, which needs **~27 battles PER ARM** at 80% power.
`arc_deg` shows nothing at all.

This restates, with numbers, what the b1-b14 entry already said: none of these runs supports a claim
about any parameter. The difference is that the machinery to settle it now exists.

- [ ] To actually settle it: plumb `target_sep` through `bbspots.plan()` -> `one_flank()` (it already
      takes the argument; `plan()` just does not pass it), alternate tight/wide per battle in
      `farm.py`, and run ~54 battles unattended (~3 h). Every one self-labels.
- [ ] Builder Base ECONOMICS are the bigger obstacle: per-battle elixir gain is **0** — BB elixir only
      arrives via the 9-star track (270k per completion) — so 90% of the 5,500,000 elixir cap is ~30
      battles, and 90% of gold from 239,380 would be 60-150. Home Village is ~20 battles by contrast.

## FARM.PY LIVE RUNS s1/s2 (2026-09-19) — THE LOOP WORKS

`scratchpad/farm.py`, real phone `EQEMVG6HSOUO9DT4`, Home Village, unattended.

| run | cycle | rc  | gold       | elixir   | dark    | child s | wall s |
| --- | ----- | --- | ---------- | -------- | ------- | ------- | ------ |
| s1  | 1     | 0   | +1,749,415 | +782,720 | +13,210 | 183.9   | —      |
| s2  | 1     | 0   | +938,278   | +673,815 | +12,850 | 204.6   | 295.3  |
| s2  | 2     | 0   | +536,709   | +816,146 | +6,299  | 198.8   | 293.9  |

**3 battles, 3x `status: ok`, `fails=0` throughout.** Gold 2,368,228 -> **5,592,630** (10.3% -> 24.3%
of the 23,000,000 cap), elixir -> 4,044,957 (18.4%), dark -> 156,011 (**40.0%**, the closest row).
Gems 810 unchanged across all three — no accidental spend.

**Wall clock is ~295 s per cycle, not the ~200 s the child reports.** The difference is base search
(`loot.search` Nexts) plus the supervisor's own 4 s settle and resource re-reads. At ~9,500 dark a
battle, 90% of dark (351,000) is roughly **20 more battles, ~100 minutes**.

- **Launch-from-cold works.** s2 started with `app_pid() is None`; `farmlib.ensure_foreground` started
  the game, the first frame was a loading screen, `recover()` logged one `recover_wait` and settled
  on HOME_VILLAGE. That is the ladder doing its job on its first real exercise.
- **Lightning fires in full on a normal base.** Both s2 battles: 4 ADs found, 4 zap events,
  **11/11 Lightning taps**. The c234418 snow base (0 ADs, 0 zaps) is the outlier, not the norm —
  do not read that one battle as a systemic Lightning failure.
- **Fixed after s1:** the child's `rec.json` carries its own `secs`, which collided with the
  supervisor's `secs=` kwarg and raised `TypeError` at the `battle_end` log line **after a
  successful battle** — the run was lost at the last step. Child fields are now `child_*`.
- s2 was run with `nohup ... &` and polled, deliberately: a foreground tool timeout would kill the
  child mid-battle, which is the one thing `batch.py` says never to do.

## AD RESCUE VIA OPENCODE (2026-09-19) — MEASURED, AND IT DOES NOT SHIP

Home Village. Prompted by live battle c234418: an icy winter base, every building wearing a snow or
cake skin, **0 Air Defenses across all five scan views**, no zaps planned, and all **11 Lightning
left in hand** — the owner dropped them by hand. Cause is the documented one
(`coc/vision/CLAUDE.md`): the detector is trained on GREEN sceneries.

**Verdict: `scratchpad/adrescue.py` exists, is measured, and is wired into NOTHING.**
`vlm.BACKEND` still defaults to `"openrouter"`, so no live path changed.

| base                          | raw zen boxes | corroborated | recall                | time        |
| ----------------------------- | ------------- | ------------ | --------------------- | ----------- |
| a13 view_mid (green, truth 4) | 5             | 4            | **4/4 precision 4/4** | 61.5 s      |
| c234418 view_mid (snow)       | 12            | **1**        | ~1 of a likely 4      | **341.9 s** |

It is excellent on bases that do not need it and 6x too slow on the one that does. The prep window
is ~54 s.

### Three things worth keeping from the attempt

1. **A one-shot whole-frame call is not a detector — re-confirmed the hard way.** My first version
   asked Zen for AD boxes in one call: **0 of 4** on a13, surviving boxes 100 px and 195 px out,
   aspect ratio INVERTED (115x52 against a true ~70x115). `coc/vision/CLAUDE.md` already said this
   ("the one-shot version scored 65% precision / 65% recall"). Using the staged
   `locate_buildings(detector="vlm")` pipeline instead took it from 0/4 to 4/4.
2. **Model skill does not transfer between jobs.** `glm-5.3-flash` won the screen-reading bake-off
   68/68 and manages **1 of 4** here. `qwen3.8-flash` gets **4 of 4 at 0-7 px**, three runs of three.
   Reading a HUD and localising a building are different abilities — never carry a model choice
   across task types without re-measuring.
3. **Sub-threshold corroboration works.** Zen alone is stochastic: precision 4/6, 4/9, 4/8 over three
   runs on IDENTICAL input. Keeping only boxes the local net also sees in its review band
   (conf >= 0.25, below the 0.80 it cannot clear on a skinned base) gave precision **4/4** on a13 and
   killed 11 of 12 hallucinations on the snow base. The filter is sound; the recall underneath it is
   not.

### `coc/vision/vlm.py` — opt-in Zen backend at the `_complete()` seam

Additive, shared foundation. `BACKEND = os.environ.get("COC_VLM_BACKEND", "openrouter")` — **default
unchanged**, so `locate.py`, `cli.py` and the tests behave identically. `COC_VLM_BACKEND=zen` routes
`ask`, `ask_list`, `read_battle_result` and all four locate stages through `coc/vision/zen.py` at
once, with no change to any call site. `COC_ZEN_MODEL` (default `glm-5.3-flash`) and `COC_ZEN_PLAN`
(default `go`) select the model. `max_tokens` is floored at 2000 — a reasoning model spends the
output budget thinking and returns empty JSON at 300.

Gates after the edit: `tests/` **15 passed**.

- [ ] Lightning still goes unused on skinned/non-green bases. Options not taken: Next past them
      (costs 1,400 gold/Next), or fine-tune the detector on skins (the standing `TODO` item).
- [ ] If revisited: the bottleneck is the tiling stage's call count, not the model. `workers` 6 -> 16
      took a13 from 136 s to 89 s; 16 -> 24 changed nothing.

## FARMING SUPERVISOR (2026-09-18) — CROSS-BASE, CALIBRATED, NOT YET RUN LIVE

One command that attacks until a storage is ~full: `scratchpad/farm.py`. Cross-base, so it belongs
to neither — **no Home Village or Builder Base attack file was edited.** Shared edits are additive
and all three gates re-run green: `tests/` **15 passed**, `scratchpad/bb/test_bb.py` **63 passed /
12 skipped**, `scratchpad/{test_battle_clock,test_spots}.py` **123 passed**.

| file                           | what                                                                                       |
| ------------------------------ | ------------------------------------------------------------------------------------------ |
| `scratchpad/farm.py` (259)     | the supervisor: startup, base detect, done-rule, battle subprocess, recovery, `farm.jsonl` |
| `scratchpad/farmlib.py` (69)   | `startup()` / `ensure_foreground()` / `grab()`                                             |
| `scratchpad/farmcaps.py` (159) | one-time capacity calibration                                                              |
| `scratchpad/caps.json`         | generated, dated                                                                           |
| `coc/vision/screens.py`        | **+`Screen.BUILDER_BASE`, +`which_base()`**. `classify()` untouched                        |
| `coc/builder_base.py`          | **+`BB_RESOURCE_ROIS`, +`read_bb_resources()`**                                            |

### MEASURED: storage caps, read off the phone (live, 2026-09-18)

Tapping a resource bar opens a panel showing Max / production / treasury. The **existing digit atlas
reads it unchanged** — identical value across four ROI paddings, no new perception needed.

|                     | max            | live now            | 90% target |
| ------------------- | -------------- | ------------------- | ---------- |
| Home Village gold   | **23,000,000** | 2,368,228 (10.3%)   | 20,700,000 |
| Home Village elixir | **22,000,000** | 1,772,276 (8.1%)    | 19,800,000 |
| Home Village dark   | **390,000**    | 123,652 (**31.7%**) | 351,000    |

The panel anchors below the tapped row (Max box = tap_y+61 .. tap_y+101, x 2040-2270) and **does not
auto-dismiss** (still open at t+14 s). **Re-tapping the same bar closes it** — that is the close
used, because it reuses a coordinate already proven safe instead of tapping the village. All three
rows read on the first live run. Builder Base caps are NOT yet read (requires being on that base).

At the measured Home Village medians (+1,002,042 gold, +916,008 elixir, ~+12k dark per battle over
24 recorded battles) every row converges on **~18-21 battles, roughly an hour**.

### MEASURED: `which_base()` — 0 wrong-base answers in 68 frames

The discriminator is the **fourth HUD row**: Home Village is gold/elixir/dark/gems, Builder Base is
gold/elixir/gems, so the HV gems ROI (y 342-378) is legible only in the Home Village. A HUD fact, so
camera-independent. A legible gems row alone proves Home Village; without it, gold AND elixir must
both parse before naming the Builder Base; anything else is UNKNOWN.

| frame set            | n   | result                     | wrong base |
| -------------------- | --- | -------------------------- | ---------- |
| Builder Base village | 28  | 24 BUILDER_BASE, 4 UNKNOWN | **0**      |
| Builder Base battle  | 27  | 27 UNKNOWN                 | **0**      |
| Home Village (+live) | 13  | 5 HOME_VILLAGE, 8 UNKNOWN  | **0**      |

**A live frame forced the design.** A real Home Village frame read gold/dark/gems but `elixir` came
back None; a first version demanding gold AND elixir before looking at gems called it UNKNOWN.
`classify()` keeps the same slack ("three of four, not four") for the same reason.

### MEASURED: `read_bb_resources()` — exact on the b1-b14 progression

**10/10 reward deltas** match the b1-b14 table, **10/10 chain checks** (`r1[bN] == p0[bN+1]`), gems
809 throughout, final gold **4,256,653** exactly. 24/28 frames readable; the 4 misses are popup-
occluded HUDs and correctly return None.

**The module docstring was half-wrong and is now corrected in place.** Gold and elixir do NOT sit
~100 px higher in the Builder Base — they are at the SAME y as the Home Village. Only the gems row
moves up, into the slot the Home Village spends on dark elixir. That is exactly why
`read_resources()` on a Builder Base frame reports **`dark` = 809, which is the gem count**.

### SAFETY BUG FOUND AND FIXED IN NEW CODE

`farmcaps.py` originally claimed the Builder Base gems row "sits on `GEM_BUY_ZONE`" and was therefore
protected. **False.** `GEM_BUY_ZONE` is (1990,225,**2075**,305); the row centre is (**2092**,261),
17 px past its right edge, and `is_forbidden()` returns False for it. `roi_centre()` now RAISES for
any gems row in either base. The Home Village claim was true — (2147,360) is inside `NO_TAP_ZONES`.
Also fixed: Builder Base taps now use `bbtap.BBTap`, not `safety.Tapper`, whose zones are Home
Village coordinates.

### Boat switching: NOT SHIPPED — it failed its validation gate

`assets/templates/boat_builder_base.png` scores true-positive **0.1897** against a best false
positive of **0.2496** (TM_SQDIFF_NORMED) — a margin of **0.060**, against the shipped `loot_bubble`
standard of 0.143 vs 0.196. It is unmasked, ~1/3 occluded by HUD bars, **visible in only 1 of 14**
stored Builder Base entry frames, and there is **no Home Village boat template at all**. Per the
plan's own gate, `farm.py` therefore ships `--switch off`: it farms the base it finds, reports, and
stops. Switching needs a mask, a second template, and a pan survey first.

### No OpenRouter, verified by execution not by reading

`deploy_targets()` was run with `requests.post` monkeypatched to raise and the key unset: **4 and 9
detections returned, no exception**. `locate_buildings("town_hall")` raises `VLMError` as expected,
confirming the harness works. Neither runner imports `vlm`. One latent landmine: `autoloop2.py`
holds a live OpenRouter endpoint in `decide()`, which `attack7` imports but never calls — so
`farm.py` blanks `OPENROUTER_API_KEY` in the child env, to fail loudly rather than spend.

### Open

- [ ] **A stale `scratchpad/STOP` from 2026-09-15 22:42 blocks every run.** It is batch.py's halt
      flag; farm.py honours it. Owner must decide whether to clear it.
- [ ] Live run: `--dry-run`, then `--max-cycles 1`, then the real loop. **NOT DONE — no battle has
      been fought by the supervisor.**
- [ ] Builder Base caps (run `farmcaps.py` while on that base).
- [ ] Regression tests for `which_base` / `read_bb_resources` in `tests/`; `is_done` is 7/7 offline
      but only as an ad-hoc check, not a gate.

## OPENCODE ZEN/GO BACKEND (2026-09-18) — MEASURED: `glm-5.3-flash` WINS, 68/68 + 13/13

Base-neutral infrastructure: new `coc/vision/zen.py` + `scratchpad/zenbench.py`. **No existing file
was edited**, so neither base's behaviour can have moved; both gates re-run green anyway
(`tests/` 15 passed, `scratchpad/bb/test_bb.py` 63 passed / 12 skipped).

**The SDK the owner linked is the wrong product.** `@opencode-ai/sdk` is a TypeScript client that
drives a local opencode CODING-AGENT server on `127.0.0.1:4096` (`session.create`, `session.prompt`,
`tui.showToast`). It is not a model API and there is no Python build. The inference product is
**OpenCode Zen**, key `OPENCODE_API_KEY`, root `https://opencode.ai/zen`.

**Zen does not serve one API — it routes each model to its VENDOR'S endpoint.** Transcribed from
the docs table, 69 API-reachable ids in four families:

| endpoint                   | SDK                   | models                                       |
| -------------------------- | --------------------- | -------------------------------------------- |
| `/zen/v1/messages`         | `anthropic`           | claude-\* **and every qwen3.x**              |
| `/zen/v1/responses`        | `openai`              | gpt-5.x/6, grok, muse-spark                  |
| `/zen/v1/models/<id>`      | `google-genai`        | gemini-3.x                                   |
| `/zen/v1/chat/completions` | `openai` (compatible) | deepseek, glm, kimi, minimax, mimo, nemotron |

**Prefix does not predict protocol** — `qwen3.5-plus` speaks Anthropic Messages. `zen.family()`
therefore matches an explicit id set and RAISES on anything absent, rather than guessing. Base URLs
verified against the installed SDKs: `anthropic` appends its own `/v1/messages` so its base is
`/zen`; `openai` takes `/zen/v1`.

**Catalogue (models.dev/api.json, the file opencode itself reads): 103 models, 65 take image input.**
The Zen docs page's own summary claims only `deepseek-v4-flash-vision-exp` does — that is wrong, do
not trust it. Several free ids the TUI offers (`qwen3.6-plus-free`, `kimi-k2.5-free`,
`minimax-m3-free`, `x-preview-f-free`) are ABSENT from the endpoint table and so are not reachable
over the API.

**Price alone picks losers here.** Cross-referencing the sub-$0.30 vision models against the
2026-09-10 OpenRouter sweep above: `gpt-5-nano` was rejected (reasoning ate the whole token budget,
empty content), `deepseek-v4-flash-vision-exp` was rejected (19-54 s), and in the locate work
`gemini-3.5-flash` scored 0/9 and `gemini-3.8-flash` 0/9 on JSON discipline. All are in the bench
anyway and flagged `RETEST`: Zen's claim is that it serves a given model better than a generic
router, so the verdict has to be re-earned. `zen.py` pins `reasoning={"effort":"low"}` on gpt-5.x,
which is the specific cause of the old empty-content failure.

**The bench scores two jobs on stored frames, no phone needed.**
`SCREEN` 68 frames / 4 classes; `RESULT` 13 frames, truth = the b2-b14 stars+damage table above.
`p0_entry` and `r1_after_return` are **deliberately ONE class** (`own_village`): they are the same
screen with the same HUD, differing only in the star counter and gold, so scoring them apart would
measure clairvoyance rather than perception. Frames go over the wire as **36.9 KB WebP** at 1100 px
(`vlm._encode`, reused) against ~2.4 MB raw.

**The account holds an OpenCode GO subscription, not Zen credits.** Plain Zen returns
`CreditsError: Insufficient balance` on every family; the key in the vault is 67 chars and so is the
`opencode-go` entry in `~/.local/share/opencode/auth.json`. Go is `/zen/go/v1`, ONE
OpenAI-compatible endpoint, and it needs an **`x-opencode-session` header plus a non-generic
User-Agent** or it 400s `MissingSessionID`. Its docs scope it to coding-agent traffic; the owner was
told and chose it for this workload anyway (2026-09-18).

### Results — 81 stored frames per model, no phone involved

RESULT = stars + damage off 13 `r0_result` frames (truth = the b2-b14 table below).
SCREEN = 4 classes over 68 frames. `$/1k` uses the gateway's OWN reported token counts.

| model                          | RESULT stars/dmg  | SCREEN    | p50             | $/1k frames     | errors  |
| ------------------------------ | ----------------- | --------- | --------------- | --------------- | ------- |
| **`glm-5.3-flash`**            | **13/13 · 13/13** | **68/68** | **2.86-3.00 s** | **0.134-0.146** | 0       |
| `omen-alpha`                   | 13/13 · 13/13     | 68/68     | 2.71-3.40 s     | 0.188-0.216     | 0       |
| `qwen3.8-flash`                | 13/13 · 13/13     | 68/68     | 3.87-5.25 s     | 0.156-0.211     | 0       |
| `minimax-m3`                   | 13/13 · 13/13     | 67/68     | 2.82-4.20 s     | 0.437-0.451     | 0       |
| `mimo-v2.5`                    | 13/13 · 13/13     | —         | 8.22 s          | 0.193           | 0       |
| `deepseek-v4-flash-vision-exp` | 12/13 · 13/13     | 66/68     | 2.54-2.95 s     | 0.129-0.225     | 1 empty |

Dead on this account: `gpt-5.6-luna` (500 on all 13), `qwen3.5-plus` ("Model is unavailable"),
`muse-spark-1.2/1.3-contributor` (403, needs a data-collection opt-in), `ox-alpha-free`
("not supported"). Total spend for the whole exercise was **under $0.40**.

**`glm-5.3-flash` is the pick**: perfect on both jobs, cheapest measured, ~3 s, 0 errors in 81 calls.

### Two traps this sweep walked into, both caught

1. **`max_tokens=300` was starving the reasoning models, and it looked like model failure.**
   `mimo-v2.5` 6/13 and `deepseek-v4-flash-vision-exp` 8/13 with truncated JSON (`'{"damage_pct": 100'`)
   and empty completions at exactly `out: 300`. At 2000 the same models are 13/13 and 12/13, zero
   errors. **Never grade a model at a budget it spent thinking.**
2. **A shared wrong answer is a bad LABEL, not a bad model.** `glm-5.3-flash` and `omen-alpha`
   independently called `b2_20260918/p0_entry` a `start_attack_dialog` where the stem said
   `own_village`. Opening the frame: b2's runner grabbed it AFTER the Start Attack panel opened —
   **the models were right**, and 67/68 became 68/68. `zenbench.LABEL_OVERRIDE` records it.

**`deepseek-v4-flash-vision-exp` is ~10x faster on Go than on OpenRouter** — 2.54-2.95 s against the
19-54 s that got it rejected on 2026-09-10. A model's verdict does not transfer between gateways,
which is exactly why the rejects were re-tested instead of inherited.

### Still true, and unchanged by any of this

These numbers say the models READ a settled screen perfectly. They say nothing about aiming: the
2026-09-10 finding (3 of 30 deploy points on legal ground, median miss 29 px) stands, and
`deploy_targets()` stays model-only local YOLO. **Nothing is wired in** — `classify()`, `locate.py`
and `vlm.py` are untouched, and both gates are green (`tests/` 15 passed, `scratchpad/bb/test_bb.py`
63 passed / 12 skipped).

```bash
OPENCODE_API_KEY="$(credvault get OPENCODE_API_KEY)" \
  python3 scratchpad/zenbench.py --task both --plan go --max-tokens 2000
```

- [ ] Decide whether `glm-5.3-flash` replaces or backs up `gemini-3-flash-preview` in `vlm.py`
      (add a `backend=` argument, default unchanged, so neither base moves).
- [ ] The pre-battle scouting and in-loop-fallback jobs the owner picked are still unbuilt; only the
      two offline jobs are measured.

## BUILDER BASE ATTACK — b1-b14 (2026-09-18): GOLD TARGET 4,200,000 MET (4,256,653)

Builder Base work, Home Village files untouched (root `CLAUDE.md` "Base scoping"). New code, all
Builder Base-scoped: `scratchpad/bb/attack1.py` (runner), `bbspots.py` (where to drop), `bbtap.py`
(interlock + fast frames). Nothing in `coc/` changed. Run:
`python3 -u scratchpad/bb/attack1.py scratchpad/bb/battles/<id> 2>&1 | tee .../console.log`
(`--dry-run` stops before Find Now!).

| battle | plan                                   | deployed | abilities        | result      | gold     | note                                     |
| ------ | -------------------------------------- | -------- | ---------------- | ----------- | -------- | ---------------------------------------- |
| b1     | `base_hull`, sep **114.8** px          | 7/7      | **none** (crash) | 2★ 54%      | +75,000  | `log()` TypeError one tap after deploy   |
| b2     | grass ring, sep 197.6 px, arc 40°      | 7/7      | T+16.8, 25.6     | **3★ 100%** | +115,000 | stage 2 ran and was MISSED               |
| b3     | grass ring, sep 231.9 px, arc 40°      | 7/7      | T+15.8, 26.4     | 2★ 83%      | +75,000  | army dead by T+57, battle self-ended     |
| b4     | grass ring, sep 266.3 px, arc 56°      | **3/7**  | T+16.5, 27.5     | 0★ 29%      | 0        | banner row y=176 + x=80 ate 4 taps       |
| b5     | margins fixed, sep 201.4 px            | 7/7 ✔    | T+17.0, 25.6     | 0★ 38%      | 0        | per-card proof landed: 43.6-65.5         |
| b6     | + T+10 ability pass, sep 216.1 px      | 7/7 ✔    | T+12, 19, 29     | 0★ 33%      | 0        | all 7 abilities fired, still a hard base |
| b7     | + measured base centre, sep 194.1 px   | 7/7 ✔    | T+12, 21, 30     | 1★ 61%      | +30,000  |                                          |
| b8     | same, sep 214.3 px                     | 7/7 ✔    | T+12, 21, 27     | 2★ 66%      | +75,000  | filled the 9-star track                  |
| b9     | + popup guard, sep 219.5 px            | 7/7 ✔    | T+12, 20, 29     | 2★ 59%      | +75,000  | all 3 passes hit all 7 slots             |
| b10    | same, sep 194.6 px                     | 7/7 ✔    | T+13, 20, 30     | 2★ 56%      | +75,000  |                                          |
| b11    | same, sep 217.0 px                     | 6/7      | T+12, 21, 29     | 1★ 49%      | +30,000  | FALSE stage 2 on the result screen       |
| b12    | **hall-aimed**, bearing 144°, 135.2 px | 7/7 ✔    | T+12, 20, 28     | **3★ 100%** | +115,000 | real stage 2 REFUSED by the new guard    |
| b13    | texture ring, sep 228.3 px             | 7/7 ✔    | T+12, 20, 29     | 2★ 79%      | +75,000  |                                          |
| b14    | hall-aimed, bearing 15°, 225.7 px      | 7/7 ✔    | T+12, 21, 29     | 2★ 56%      | +75,000  | guard correctly refused a false stage 2  |

Damage 54, 100, 83, 29, 38, 33, 61, 66, 59, 56, 49, 100, 79, 56 — mean **62%**, and the historical mean over 11 runs is 79%
at sd 27, so **none of these runs supports a claim about any parameter**. What is proven is
mechanical: 7/7 units deployed and confirmed per card in b5-b8, abilities fired in every stage, and
no tap refused in 14 runs. **Owner's target was 4,200,000 gold: met at b14 — 2,899,241 →
4,256,653 (+1,357,412)**, elixir 1,533,830 → 2,073,830 (+540,000), **gems 809 unchanged** (no
accidental spend). The 9-star track filled TWICE, paying 270,000 gold + 270,000 elixir each time;
it resets and keeps paying, so there is no daily cap to work around.

**The daily star track pays 270,000 gold + 270,000 elixir at 9 stars and RESETS** (7/9 → b7 1★ →
8/9 → b8 2★ → paid, back to 1/9). So attacks keep earning; there is no daily cap to respect.

### Live facts measured today

- **Army is Battle Machine L30 + 6 Baby Dragons L18** (4× zoom on the Start Attack card: builder in a
  wooden cockpit, hammer arm, no rotor). The `TODO`/`flows` note "ALL AIR: 6 Baby Dragons + 1 Battle
  COPTER" is the STAGE 2 hero: b2's stage-2 frame shows the Copter card fresh at slot 0. So stage 1
  fights with a GROUND hero and the old ground/air pairing argument holds for it.
- **The Builder Base battle clock is 2:00**, not 3:00 (`p2_prep` frames: "Battle ends in 2M 0s").
- **Stage 2 gives a fresh hero AND 8 dragon cards** (9 slots), not 2 extra cards (b2 t≈179 frame).
- Matchmaking to first battle frame: **62.4 / 62.9 / 63.2 s** over three runs.
- `ATTACK_BUTTON (206,957)`, `FIND_NOW (1663,709)`, `RETURN_HOME (1195,909)`, `red_close (1869,200)`,
  `green_confirm (1578,729)` all still correct. Attacks are still free.

### Fixed, with the measurement that forced it

- **`builder_base.base_hull` is unusable for deploy planning.** On b1's prep frame its red mask held
  802 components and the LARGEST was the **Surrender button** (10,990 px at (111,719,221x69)); the
  hull came out (42,110)-(2213,860) = 53% of the screen, `deploy_points` clamped **64 of 72** angles
  onto the screen edge, and the army went down at 114.8 px. Replayed over all 8 stored prep frames
  the old path gives **94.5-149.3 px**, always under the 190 px Tantrum floor.
  Replaced by `bbspots`: per angle, walk INWARD from the play-area border to the outermost point
  whose 60×60 window is ≥ 0.60 grass (measured: left margin 0.99, right margin 0.62, base interior
  0.04). 25-49 candidates per frame, plan in 110-205 ms, separation 191.9-232.6 px on all 8 frames.
- **One flank, tightest arc that clears 190 px** — not the widest spread (b1's frame offers 382 px).
- **Angles are measured from the base, not the screen.** `bbspots.base_centre()` = centroid of the
  dense non-grass area, clamped to 300 px. Measured centres b1-b6: (1175,481) (1188,506) (1117,553)
  (1124,517) (1221,527) **(1434,574)** — b6's base sat 238 px off the old constant.
- **Never tap above y=250 or within 150 px of the left/right edge.** b4 put the hero at (119,176)
  and two more units on that row, where an Android **notification banner** (Telegram) was sitting,
  and one at (80,804): exactly those four never deployed, and the three that landed were all at
  x ≥ 238, y ≥ 259.
- **Deploys are proven PER CARD.** b4's batch-level check passed (bar delta 19.1) while 4 of 7 units
  sat in hand. Card-crop mean |diff| on b4's own frames: **landed 48.0 / 48.4 / 48.9, in hand
  10.2 / 10.3 / 11.8**, and 35.9 for a card left merely selected. Threshold 40, one retry that
  `avoid`s the failed point by 120 px. b5-b8 then deployed 7/7 with diffs 43.6-70.2.
- **`log()` crash:** `dict(t=..., **kw)` raised TypeError when a caller passed its own `t`. It killed
  b1 one tap after the deploy, so no ability ever fired. Now `setdefault`.
- **Stage-2 detection needs ONE revived card, not two.** b2 card saturation: hero slot S=86 at T+4,
  **S=2 at T+53** (dead), **S=89 at T+97** (stage 2's fresh Copter). The two EMPTY slots read S=99-114
  off the background and never went dead, so "≥2 revived" never fired and a whole stage went unused,
  repeating r10. Now a slot must read dead twice running, and one confirmed revival opens the stage.
- **Ability schedule T+10 / T+18 / T+26** (was T+14/24). b5 lost 3 of 7 units before its T+17 batch,
  so their abilities were never used. A repeat tap on a spent ability is inert. HYPOTHESIS, not a
  measured gain.
- **The Star Bonus popup blocks the next run.** A green centre button with NO red X is a village
  popup, not Start Attack (which always shows both). Dismissed on entry; measured "Okay" (1198,857).
- **The review loop logs the alive vector every iteration** — without it b2's lost stage was
  invisible in the record and had to be reconstructed from frames.

### The Builder Hall is a star by itself (2026-09-18)

Stars are NOT monotonic in damage: b7 61% → **1★**, b1 54% → **2★**. The rule is 50% damage, the
Builder Hall, 100% — so the hall is a whole star on its own, and stars are what the rewards pay:
0★ → 0, 1★ → 30,000, 2★ → 75,000, 3★ → 115,000, plus the 9-star track's 270,000 + 270,000.

- **`bbspots.builder_hall()`**: the hall's orange roof is the one large saturated-orange object on a
  Builder Base battlefield. MEASURED on the ten b1-b10 prep frames: largest orange component is the
  hall **10/10** (verified by eye at 2x), area 8,694-16,806 px, runner-up 3,621-8,065, margin x1.3
  to x3.4. It refuses rather than guesses when the margin is under 1.2 (b11: no call).
- **`hall_side()` aims the wave at it** when the hall is ≥150 px off the base centre — on five of
  thirteen bases. b7 is why: its hall sat 781 px off centre and the old planner put the whole army
  170° away, scoring 61% and one star with the hall untouched. Live in b12: hall (921,652),
  bearing 144°, `aimed: true`.
- **Aiming deliberately drops below the 190 px Tantrum floor** (that flank is often narrow) but never
  below `SPLASH_FLOOR` 120 px — a tile is ~38 px, so that still clears Air Bomb splash (57 px),
  Roaster splash (46 px) and the Mega Tesla chain (114 px). Being splashed as a group is a worse
  trade than losing a damage bonus that eleven recorded runs could not detect.
- **Effect on stars is UNMEASURED.** b12's 3★ was not even aimed (hall too central). ~16 runs per arm.

### Colour was scenery-bound; texture is not (2026-09-18)

`bbspots` keyed the ground on a green HSV range. b12's **stage 2 was fought on blue-grey ice**, where
that range matched the ground AND the buildings: the base mass vanished, `centre_measured` went
false, and the stage-2 guard refused a REAL stage 2 for 65 s — a fresh Battle Copter and 8 dragons
never deployed. Same trap as the Home Village a9 blue base.

Ground is now detected by **edge energy** (blurred Laplacian, 61×61 box): open ground scores < 12,
a base is 510k-1.33M px above it, on green and blue frames alike. Ring resolution 4° → **2°**
(candidates 25-42 → 50-106; worst-case separation 164 → **190 px**, so every stored base clears the
Tantrum floor), costing ~0.4 s at T=0 and 0.9 s worst case at a stage change.

### Stage-2 detection: one revival, then two guards

- b11 fired a stage 2 at T+121 **on the result screen** — cards read alive there too — and sent 8
  taps into it. Now a revival is confirmed on a FRESH frame by `looks_like_battle()`: `in_bb_battle`
  (which reads False on the result screen and is what actually catches this) plus a measured base
  mass and a loose candidate bound.
- The first version of that guard used the colour ground test and blocked b12's real stage 2. Both
  the false positive and the false negative are now in the gate as tests.

### Next — Builder Base (ordered, 2026-09-18)

1. **Drive a stage 2 live.** Four have now occurred (b2 missed by the old rule, b11 false, b12
   blocked by the colour-bound guard, b14 correctly refused) and the deploy path has still never
   executed. It needs a 3★ stage 1 — 2 of 14 today. Everything is in place; it is a matter of
   running battles. Judge it by "Troops expended" showing the Copter + stage-2 dragons.
2. **Destroy the O.T.T.O Outpost in stage 2** — still the only known unclaimed star. Visible in b7's
   prep frame as a separate small building inside its own red boundary segment on the far right.
   Needs a stage 2 first.
3. **Measure whether hall-aiming pays.** It fires on ~5 bases in 13 and is mechanically verified;
   the star effect is unknown. The clean metric is the HALL-KILL RATE (stars ≥ 2 while damage < 100),
   9 of 14 today — a discrete per-battle outcome, far cheaper to power than damage %.
4. **Fix `classify()` for the Builder Base** (shared `coc/vision/screens.py`): it returns
   HOME_VILLAGE on a Builder Base frame, so nothing stops a Home Village flow running here. Additive
   change only, and it needs the Home Village gate re-run (base-scoping rule).
5. **Detect the card centres instead of assuming them.** Stage 2's 9 slots measured
   [430, 601, 753, 905, 1049, 1201, 1362, 1513, 1659]; the constants are 17-18 px out at the two new
   slots — inside the ±68 px card today, but it is an assumption, not a measurement. A bar-profile
   detector was prototyped and works (runs found at those exact centres).
6. **`builder_base.modal_present()` misses real panels** (returned False on an open "Suggested
   upgrades" panel). Low priority: the runner keys on buttons, not panels.
7. **A Builder Base defence detector** would let the flank be chosen by threat rather than geometry.
   The Home Village YOLO model does not transfer (different buildings), and `assets/bb_defenses.json`
   has game facts but no templates. This is the big one and it is unstarted.
8. **Do not tune the planner on single runs.** The three things that look tunable — separation,
   deploy distance, ability timing — have all been measured; two are dead and the third is a
   hypothesis. Collect ~16 runs per arm or leave it alone.

### Killed hypotheses

- **"The grass ring deploys too far out, so units die on the approach."** FALSE, twice over. Distance
  to the base CENTRE: b5 0★ **711 px** (the shortest of all), b2 3★ 899, b4 0★ 901, b3 2★ 928.
  Distance to the base EDGE, which is what an approach actually costs: ≥2★ mean **281 px** (n=6) vs
  ≤1★ **328 px** (n=4), ranges overlapping (b1 2★ at 47 px, b6 0★ at 566, b3 2★ at 441).
  Neither distance nor separation orders outcomes.

### Not verified

- **The stage-2 deploy path has still never run live.** Three stage 2s have now occurred (b2 missed
  by the old rule, b11 false, b12 refused by the colour-bound guard). The detector and both guards
  are covered offline against b2's, b11's and b12's own frames; the deploy itself is untested live.
- **Whether hall-aiming raises the star yield.** Implemented and mechanically verified (b12 bearing
  144°, b14 bearing 15°, both `aimed: true`); no outcome evidence. Hall-kill rate 9 of 14.
- b14 DID show the stage guard working as designed: `new_stage_refused` at T+61 with
  `in_battle: false` — b11's exact failure mode, now caught. The fix is covered offline by `test_bb.py::test_one_revived_card_opens_stage_two_and_two_does_not`,
  replaying b2's own frames, but no live stage 2 has been driven.
- Whether any of today's changes improve the OUTCOME. Base difficulty dominates (sd 27).
- `coc/vision/screens.py:classify()` returns **HOME_VILLAGE on a Builder Base frame** — shared file,
  not touched. Nothing stops a Home Village flow running here.
- `builder_base.modal_present()` missed an open "Suggested upgrades" panel (returned False).
- Card x positions shift with the number of cards: stage 2's 9 slots measured
  [430, 601, 753, 905, 1049, 1201, 1362, 1513, 1659] vs the constants' [.., 1531, 1676] — 17-18 px
  out at the two new slots, inside the ±68 px card, so it works today but is not measured-safe.

### Gate

`cd scratchpad/bb && PYTHONPATH=../.. python3 -m pytest test_bb.py -q` → **56 passed, 9 skipped**
(2026-09-18); `python3 -m pytest tests/ -q` → 15 passed (shared layers untouched).
Contracts live in [`scratchpad/bb/CLAUDE.md`](scratchpad/bb/CLAUDE.md).

## LIVE ATTACK SYSTEM — STATE AFTER a9-a15 (2026-09-17)

Code: `scratchpad/attack7.py` + `strategy.py`, `zaps.py`, `targets.py`, `spots.py`, `camera.py`,
`hud.py` (contracts: `scratchpad/CLAUDE.md`). Gate: `test_battle_clock.py` + `test_spots.py` 82 passed,
`pytest tests/ -q` 15 passed. Details of every battle and fix are further down.

| battle | code                                | scenery | result          | loot (g / e / d)        | what it proved or broke                                                              |
| ------ | ----------------------------------- | ------- | --------------- | ----------------------- | ------------------------------------------------------------------------------------ |
| a9     | green-only spots                    | blue    | no units        | -1,400 g                | 0 grass points → 0 probes for 130 s                                                  |
| a10    | a9 fixes                            | green   | Defeat 0★ 26%   | +172k / +438k / +5.2k   | diagonal pans + relocalize ate the clock; 4 bolts/AD; first dragon 0:22              |
| a11    | a10 fixes                           | green   | Victory 3★ 100% | +827k / +482k / +10.7k  | clock fixed (dragons ~2:12); 11 Lightning vs 8 tapped (phone touched + top-up spill) |
| a12    | a11 fixes                           | green   | Victory 1★ 57%  | +715k / +521k / +12.9k  | Lightning 9 = 9 tapped; 5 dragons stuck in hand; popups pause the timer              |
| a13    | a11 fixes                           | green   | Victory 2★ 87%  | +1.98M / +688k / +669   | 11 vs 9 tapped: phone touched (confirmed by owner)                                   |
| a14    | dragon landing + 3+3+3+2            | green   | Victory 3★ 100% | +613k / +1.95M / +10.6k | 15/15 dragons; Lightning selected with no script input → 2 spares cast               |
| a15    | selection guard + spares + AD pairs | dark    | Victory 3★ 100% | +959k / +608k / +17.7k  | Lightning 11 = 11 tapped; 15/15 dragons; 0 taps under 2 popups                       |

Verified live: axis-only pans + map-edge stop (0 relocalize a12-a15); 3 bolts per L12 AD; bolts back
to back; merged/standing checks on AD lines; one dragon per tap with landing checks (a14, a15);
on-screen top-up with probe fallback (a15); popup DimGate (a15); spare bolts (a15); edge views + ring
probes on a non-green base (a15).
NOT verified live: midpoint pairing (no ADs within 100 px were found in a15); the selected-card guard
firing (no outside switch in a15).

## DARK ELIXIR GOAL — 25,095 → 204,609 DE in 14 battles (a16-a29, 2026-09-17) — DONE

Owner's goal: a Dark Elixir balance of 200,000. Verified at the end on the village HUD: **204,609**
(digit reader and by eye). a16-a18 ran the a15 code; after them the owner chose "both changes" and
a19-a29 ran them. New module `scratchpad/loot.py`, reads in `hud.py`, templates `cards/reward_*.png`.

| code          | battles | DE gained | per battle | notes                                                                                                                 |
| ------------- | ------- | --------- | ---------- | --------------------------------------------------------------------------------------------------------------------- |
| a15 code      | a16-a18 | +28,116   | 9,372      | a16 midpoint pairing fired live: 4 bolts at one pair's midpoint, the next pair already down (`standing_before` false) |
| search + pick | a19-a29 | +150,674  | 13,698     | 8 Dark Elixir picks in 4 battles; Lightning taps 11 in all 11                                                         |

Per battle a19-a29 (nexts / attacked base DE / DE picks / delta): a19 2/10,451/0/+12,151 ·
a20 10/6,133/0/+5,899 · a21 10/5,287/3/+28,422 · a22 1/10,573/0/+9,801 · a23 10/3,897/2/+15,001 ·
a24 2/10,261/0/+11,093 · a25 2/9,581/2/+8,459 · a26 1/8,734/0/+10,434 · a27 1/16,560/0/+14,591 ·
a28 1/9,866/1/+18,232 · a29 6/14,891/0/+16,591. (Not a controlled comparison: n=3 vs n=11,
different bases; the picks and the search are each verified mechanically below, not on yield.)

- **Base search (`loot.search`)**: read "Available Loot" DE while scouting, tap Next below `DARK_MIN`.
  `hud.loot_dark` walks the number's extent from the LEFT then runs the unchanged digit reader:
  8/8 exact on a11-a18 first frames (plain `read_number` 7/8 — a11 refused on a stray speck), 0
  unreadable in 57 live reads. `hud.next_button` orange fraction: >= 0.626 on 54 prep frames, <= 0.014
  on 246 others. Live: 46 Next taps, every one saw the clouds (3.0-5.5 s), 0 timeouts.
  Threshold 10k → **7k after a23**: of 46 bases then seen, 13% >= 10k (2 of 38 live), 37% >= 7k; 3 of
  a20-a23's 4 searches hit `MAX_NEXTS`=10 (~45 s, then a ~5k base). a19-a29: 57 bases, 19 >= 7k, 5 >= 10k.
- **Reward pick (`loot.RewardPick`)**: "Pick a Reward!" cards are RANDOM (troops, Gold, Elixir, Dark
  Elixir, Tag Tickets) in any slot; untouched, the game auto-picks after ~10 s (a18: Elixir, then Tag
  Tickets with 6,977 DE on offer). Templates: ribbon 22/22 popups >= 0.947, others <= 0.341; "Dark
  Elixir" label 0.976-1.000 on 13 DE cards, best other 0.635 ("Elixir"), flipping-in card 0.60.
  Hooked into every `dimmed()` site, the review loop (before the end check) and a post-battle poll
  for the 100% popup. Live: picks at 33% (mid-deploy), 66% (review loop) and 100% (after battle_over)
  all landed on the DE card (a21 frames: card highlighted, popup gone ~2 s later); the in-battle DE
  counter jumped by the card's amount (a25: 136,310 → 138,910 and 139,880 → 143,145; a21 86,804 →
  91,174); result screens agree with the deltas (a21 26,722 + 1,700 = +28,422; a25 6,827 + 1,632).
- **The owner hand-picked some popups in a16/a18** (confirmed): a16's "extra" 6,204 DE = its two
  popup DE cards exactly (6,966 base + 2,897 + 3,307 = 13,170 on the result screen).
- Gate: `test_battle_clock.py` + `test_spots.py` **118 passed** (82 + 36 new); `tests/` 15 passed.
  All 36 new tests FAIL against `battles/a18_20260917/pre_fix/` (7 replay tests via `ATTACK7_CODE`,
  29 hud tests with the pre-fix `hud.py` first on the path). Replay baseline identical to pre-fix
  (122.9 s left at first dragon, 160.7 s at first bolt, 15 dragons, 11 bolts, 0 off-AD). The replay
  gained `--dark-seq` (bases, Next) and `--popup-at T [--popup-dark]` (dimmed frames, taps swallowed).

### a29 fixes: popup-gated card taps / support / pans, review until battle_over — OFFLINE DONE, LIVE BLOCKED

Owner said "yes" to fixing both (2026-09-17). Code: `attack7.py` (review cap, stale-frame hand-offs,
gates), `loot.RewardPick.wait_out`, `replay_a10.py` (`--prep-s`, multi-popup `--popup-at`, clock freeze,
`swipes_into_popup`, `exit_while_live`). Backup of the previous code: `scratchpad/battles/a29_20260917/pre_fix/`.

Root causes (a fresh red-team agent tried to falsify each, read-only, 15 calls):

- **Review loop ended early — CONFIRMED.** `REVIEW_BUDGET` 190 s was wall clock; the 180 s battle clock
  stops for as long as a popup is up (2.4-12 s each, read from review-frame timers: a24 held "1M 57s"
  t64.3-74.3 and "1M 37s" t94.4-104.3). a24 ran to ~t201.8, a26 ~t199; the loop quit with 11 s / 8 s
  left. Killed alternatives: t0 misaligned (a24 t64.3 read 117 s vs 115.7 expected) and another loop
  exit (only `break` is battle_over; both ended status ok).
- **BACK into a live battle — NOT observed live (weakened).** a24's exit0.png shows 1 s left, but its
  mtime is ~4.4 s after result.png's "4s" and screencaps lag; only exit0 exists, so one BACK reached the
  village — consistent with BACK after the end. Reproduced only in the replay (`--prep-s 40 --popup-at
100,150`: to_village with 1.7 s left).
- **Ungated touches — CONFIRMED, wider than first reported.** Not popup-gated: group dragon card tap,
  retry card tap, `deploy_support` card + map taps, the Lightning re-select tap, and every `pan()`
  swipe (found by the red-team). Plus two stale-frame hand-offs: `find_spot` and `deploy_support`
  did not return their frames, so the next pan checked a pre-popup frame. Zaps are not gated: last zap
  <= 27.2 s, earliest popup 60.4 s across a16-a29.

Fix: gate = the RIBBON (`hud.reward_popup`), not dimming — all 39 mid-battle popups on a11-a29 review
frames showed it on their first dim frame; a dimming-based gate cost 15 s, then 3 s, on the replay's
black-bordered scan views with no popup. Review runs to `battle_over`, cap 240 s; past the cap it
waits 60 s touching nothing but a DE pick, then `finish("battle_still_live")` — never BACK.

Before → after, `PYTHONPATH=.. python3 replay_a10.py OUT [--code battles/a29_20260917/pre_fix] ARGS`:

| ARGS                             | taps into popup | swipes into popup | support never deployed     | exit while live                                           |
| -------------------------------- | --------------- | ----------------- | -------------------------- | --------------------------------------------------------- |
| (none)                           | 0 → 0           | 0 → 0             | 0 → 0                      | 0 → 0 (first bolt 160.7 / dragon 122.9 s left, both runs) |
| `--popup-at 60`                  | 1 → 0           | 3 → 0             | 0 → 0                      | 0 → 0                                                     |
| `--popup-at 70` / `83`           | 13 → 0          | 2 → 0             | 6 → 0 (Hog, Log, 4 heroes) | 0 → 0                                                     |
| `--prep-s 40 --popup-at 100,150` | 1 → 0           | 1 → 0             | 0 → 0                      | 1 → 0 (battle_over now logged)                            |
| `--prep-s 40 --battle-s 400`     | 0 → 0           | 0 → 0             | 0 → 0                      | 1 → 0 (status battle_still_live)                          |
| `--popup-at 60,120 --popup-dark` | 0 → 0           | 1 → 0             | 0 → 0                      | 0 → 0 (2 picks both)                                      |

Gate: `test_battle_clock.py` + `test_spots.py` **123 passed** (5 new); `tests/` 15 passed; all 5 new
tests FAIL with `ATTACK7_CODE=battles/a29_20260917/pre_fix`. `attack7.py` 581 LOC (wait moved to loot.py).

- **a30 (first live battle on the fix, 2026-09-17): Defeat 0★ 46%** (league-28 base, 5 ADs, 1 unzapped;
  all troops dead at t112). +37,852 g / +924,229 e / +11,147 DE; Lightning used 11 = 11 zap taps;
  15 dragons. `battle_over` logged at 112.0 (ended by troops, not the clock). One popup (ribbon on
  review 75.8-77.8), DE picked at 76.8, **0 other taps inside it**. `popup_wait`: none — the popup
  did not meet a card tap, support deploy or pan, so the new gates were NOT exercised live.
- [ ] **LIVE verification still open** (a30 did not hit either case). The screen-off block cleared.
      Needed: battles judged with `judge.py`-style checks — `battle_over` logged in every battle, a
      `popup_wait` event where a popup meets a deploy, 0 journaled taps inside ribbon spans of
      `review/`, result screen Lightning = zap taps. The frozen-clock case (2/14 battles a16-a29) may
      need several battles to occur.

### Found this session, NOT fixed (report first)

- [ ] `result.png` (6 s after the end) often shows the 100% popup instead of the result (a18, a19),
      hiding "Lightning used"; the exit frame `/tmp/<battle>_exit0.png` showed it for a26.
- [ ] Popup reward troops the game auto-picks are deployed by the game (a26: Yeti Undertaker x1 in
      "Troops expended", not in the tap journal) — not a script tap.
- [ ] Owner spent 12,000,000 gold between a25 and a26 (village read 18,834,606 → 6,834,606).

## Done

- [x] **`.gitignore` added** (2026-09-21, both bases, repo hygiene). Tracks code, `assets/`, docs and
      `tests/`: **150 files, ~54 MB** (largest the 29 MB YOLO `.onnx`), measured with
      `git ls-files -o --exclude-per-directory=.gitignore`. Ignores `runs/`, `captures/`, caches, backups
      and the GB-scale evidence dirs (`scratchpad/battles/`, `bb/battles/`, `farm/`, `yolo_survey` data)
      — the battle gates read frames from those, so they only pass on this machine.
      Open: `.git/info/exclude` still hides all of `scratchpad/`, `tests/`, `runs/`.

- [x] **Base scoping rule added to `CLAUDE.md`** (2026-09-18, owner's request). New section
      "Base scoping — one base per task, never edit the other one's files": a Builder Base task must
      not touch Home Village files (`scratchpad/attack*.py` + modules, `coc/flows/home_collect.py`,
      `coc/battle.py`, `safety.NO_TAP_ZONES`) and a Home Village task must not touch Builder Base files
      (`coc/builder_base.py`, `assets/bb_defenses.json`). Shared foundation (`config`, `device`,
      `capture`, `report`, `cli`, `coc/vision/`, `assets/digits|templates|models`, `scripts/`, `tests/`)
      may be edited additively only, with the other base's gate run and named in the summary.
      Scoping restricts _editing_, not reuse: Builder Base work is expected to import the shared
      perception stack as-is (`locate.deploy_targets()` / stage-0 YOLO, digit reader, capture,
      device, Tapper, `scripts/`, `scratchpad/` probes) and may read Home Village code for
      reference; a Home Village helper needing different behaviour gets copied, not edited.
      Doc-only change — no code touched, no device run.

- [x] Device layer: `dns-sd` rediscovery (survives the ephemeral wireless-debug
      port), battery/screen guards, input. Verified by killing the connection
      with `adb disconnect` and recovering in 12.2s.
- [x] Capture: `screencap` backend, landscape assertion, density assertion.
- [x] Digit reader: per-digit atlas, all 10 digits, aspect-preserving cells.
      Reads gold/elixir/dark/gems. 4 regression tests green.
- [x] Loot-bubble detection: masked ring template, finds gold/elixir/dark from
      one template. Measured margin 0.00-0.14 true vs 0.196 first false positive.
- [x] Safety: no-tap zones over Shop / gem-buy / Upgrade / Attack, tap jitter,
      `--dry-run`.
- [x] Screen classifier + panic path, including the inactivity-disconnect dialog.
- [x] Home Village collect flow, verified live (see Verified numbers below).
- [x] CLI: `collect`, `status`, `summary`. launchd plist + wrapper.
- [x] **Classifier fixed (2026-09-08).** `_village_hud_present()` now requires
      the resource counters to PARSE, not merely to be bright. Brightness was
      never proof that nothing overlays the village. Verified live: the League
      Overview panel went `home_village` -> `unknown`, and `ensure_village()`
      recovered from it via BACK in 16.3s instead of handing the modal to the
      flow. 24 stored frames reclassify identically (0 regressions).
      Note: screen classification now needs `assets/digits/atlas.npz`.
- [x] Navigation scout (2026-09-08): located the **Builder Base boat** and the
      **Clan Capital** balloon/island on the SW shore, and opened the four
      panels reachable from the left rail. Found the classifier defect above.
- [x] Zone audit against a live frame (2026-09-08). Every no-tap / HUD zone
      is now a MEASURED element box, not an estimate. Fixed: the shield
      timer's gem `+` was tappable; the right-edge HUD zone was ~85px off
      and covered 14px of the layout/settings buttons; the base-layout
      button and the season/boost button were uncovered.

## STAGED BUILDING LOCALISATION — `coc/vision/locate.py` (2026-09-12)

Closes the open warning in `coc/vision/CLAUDE.md` that building localisation was unvalidated —
for `air_defense`. Every other class is shipped but still UNMEASURED.

**The bug in the obvious approach.** One whole-frame VLM call returned exactly **4 air defenses on
all 5 test bases** — the right number for these town halls — while only 13 of those 20 boxes sat on
an actual Air Defense. One was a gold storage with a "2d 9H" timer, one an orange lava cauldron, one
a spell building. It was filling a quota from prior knowledge of Clash of Clans, not reading pixels.
The perfect count is what hid it, which is why the contract is now "crop every box and look at it".

**Stages** (`base_bounds` → 3x2 overlapping native-res tiles upscaled 1.6x → detect per tile → map
back to native px → NMS → re-classify each hit from its own 360 px crop).

| approach                      | precision        | recall          | $/frame     | latency   |
| ----------------------------- | ---------------- | --------------- | ----------- | --------- |
| one-shot whole frame          | 65% (13/20)      | 65%             | $0.0024     | ~7 s      |
| staged, `--no-verify`         | 86% (18/21)      | 90%             | $0.0070     | ~15 s     |
| **staged + verify (default)** | **100% (18/18)** | **90% (18/20)** | **~$0.010** | **~21 s** |

n = 5 unseen battle-scout frames captured from the phone (`adb exec-out screencap`), graded by
cropping all 21 detections at native resolution. The verify stage caught all 3 false positives
(2 X-Bows + 1 "other") and lost none of the 18 true positives.

Commands that produced it:

```bash
python3 -m coc.cli locate --image runs/<frame>.png --overlay /tmp/boxes.png
python3 -m coc.cli locate --overlay /tmp/live.png          # live grab
```

- **The confusable pair is X-Bow vs Air Defense**, and adding a class does not fix it — `x_bow` was
  already an offered label; the model simply mislabelled at full-frame scale. Zoom fixes it: on a
  360 px crop of one building the same model separates them at confidence 1.0. That is the whole
  argument for stage 4.
- **Stage 1 (`base_bounds`) is the flaky one, and my first read of why was WRONG.** I recorded that
  `gemini-3-flash` "could not" do the 5-region layout task. Measured properly afterwards — 12 calls
  per model across 3 real frames — it is **9/9**, and the one live failure was a rare flake, not an
  incapacity. `gemini-3.1-flash-lite` is also 9/9 at half the input price; `gemini-3.5-flash` is 0/9
  (answers with prose reasoning instead of JSON) and `gemini-3.8-flash` 0/9 (markdown-fenced and
  truncated at `max_tokens=600` — probably fixable with a bigger budget, not retested).
  `base_bounds()` therefore retries up to `BOUNDS_ATTEMPTS=3` and switches to flash-lite on the last
  attempt, then raises. No pro model is used anywhere in the pipeline.
- **Recall misses are stochastic, not a fixed blind spot.** Two consecutive live runs on the same
  village each found 3 of 4 air defenses — but _different_ ones (missed `(825,379)` in one,
  `(1666,624)` in the next). A union over two runs would likely reach 4/4; not implemented, but that
  is the cheap route to higher recall if it is ever needed.
- **LIVE VERIFIED 2026-09-12** against the phone with the Home Village in front:
  `python3 -m coc.cli locate --overlay /tmp/live.png` → 13 buildings in 23.2 s, air defenses 3/3 of
  the boxes correct (1 of 4 missed), overlay graded by eye. The BLOCKED path was verified too: with
  the screen off it returns `BLOCKED: expected landscape 2392x1080, got 1080x2392` and exit 2 rather
  than a traceback.
- **`loot_bubble` is measurably WRONG on the live frame** and should not be used: it boxed the four
  small resource droplets and missed every one of the large pink domes, which is the opposite of the
  class description. Either rename the class to match what it finds or drop it — the existing
  masked-template bubble detector in `templates.py` is better at this and is already verified.
- Not built: deploy-boundary detection (the white troop-deployment arc in the attack screen) — it is
  visible in the captured frames and is the obvious next target, but nothing about it is measured yet,
  so it is deliberately absent rather than shipped unvalidated.
- `vlm.py` gained `ask_list()` (JSON array) alongside `ask()` (JSON object); `_complete()` now holds
  the single HTTP path. `ask()` behaviour is unchanged.

## LOCATE STAGE 0 LANDED (2026-09-17) — local YOLO first, VLM only where it is needed

`coc/vision/yolo.py` (new) + `locate.py` stage 0 + `cli.py locate --detector {hybrid,vlm}`.
Weights `assets/models/burnt_yolov5s_26cls.onnx` (ONNX export of the surveyed model, sha256-pinned,
run through `cv2.dnn` — no new dependency). `air_defense` / `x_bow` / `inferno_tower` come from the
detector; `town_hall` / `loot_bubble` still use the VLM stages. Tests: `tests/test_yolo.py`
(stored-frame ground truth) + `tests/test_locate_hybrid.py` (stage-0 rules, VLM stubbed) —
`python3 -m pytest tests/ -q` → **12 passed**; each new test was shown to FAIL on a mutation
(threshold 0.30 / 0.95, relabel rule loosened, pre-change `locate.py`).

**Before/after, same 9 graded frames, classes air_defense,x_bow,inferno_tower**
(`scratchpad/yolo_survey/ab/ab_locate.py`; recall denominators = union of graded-true boxes):

| path                         | precise       | AD    | X-Bow | Inferno | median / max s   | VLM calls |
| ---------------------------- | ------------- | ----- | ----- | ------- | ---------------- | --------- |
| before: `detector="vlm"`     | 79/89 (88.8%) | 30/31 | 23/31 | 26/27   | 25.05 / 26.66    | 160       |
| **after: hybrid, verify**    | 82/85 (96.5%) | 30/31 | 25/31 | 27/27   | **2.72** / 14.88 | 30        |
| after: hybrid, `--no-verify` | 74/75 (98.7%) | 27/31 | 23/31 | 24/27   | **0.09** / 0.27  | 0         |

- **The old VLM path is worse than recorded.** 2026-09-12 said AD 18/18; on these 9 frames it
  called two X-Bows and a storage "air_defense" (30/34) — the exact confusion stage 4 was built for.
- **Runtime parity:** `cv2.dnn` reproduced 610/611 torch boxes (same class, IoU>0.9, dconf 0.000),
  and `yolo.detect()` 105/105 exposed-class boxes (±2 px). 82.7 ms median CPU (n=45). onnxruntime
  CoreML was 12.2 ms but drifted conf by up to 0.16 — rejected, it would cross the 0.80 line.
- **Confirm, never relabel (stage-0 verify).** First A/B run: the VLM RELABELLED 7 review-band boxes
  into another requested class and all 7 were wrong ("28s" timer → air_defense, hero cards → x_bow, a
  real X-Bow → air_defense). Rule now: keep a review box only on a SAME-label confirmation. Same-label
  confirmations: 17 true / 2 false over two runs (a gold machine → x_bow 0.74, a spiked-ball tower →
  air_defense 0.32). Rule was derived on these frames; the live base below is its first unseen test.
- Inferno's one false accept at >= 0.80 is a Bomb Tower burning mid-battle (0.82).
- **LIVE, home village** (`coc.cli locate --classes air_defense,x_bow,inferno_tower --overlay`,
  camera zoomed in by the user): 8 boxes, 8/8 true by eye (2 AD, 4 X-Bow, 2 Inferno incl. one
  VLM-confirmed), 19.4 s wall of which ~8 s is `screencap`.
- **LIVE, enemy base** (`scratchpad/yolo_survey/scout_live.py`, user-approved, 0 units placed):
  Attack → Find a Match → detect → End Battle → village. Detector 210.7 ms in-process. **10/10
  accepted boxes true** on an unseen TH14 base (AD 4/4, Inferno 3/3, X-Bow 3 of 4 — the 4th at
  0.53). Offline on the same frame: hybrid+verify 11/11 in 4.3 s (confirmed that X-Bow, rejected a
  gold machine and the timer text); VLM path 11/11 in 18.7 s. Cost: gold 13,234,433 → 13,233,033
  (**-1,400**, the search fee, nothing else). Evidence: `scratchpad/yolo_survey/live_20260917/`.
- Found, NOT fixed (pre-existing): `coc.cli locate --json --overlay X` prints `overlay -> X` after the
  JSON on stdout, so the output does not parse (`jq` fails).

## YOLO DETECTOR SURVEY (2026-09-17) — one public model is usable for defences

Question: is there a pretrained YOLO for CoC buildings that is fast AND accurate on THIS phone's
frames? Searched HF, GitHub, Roboflow Universe, Kaggle. Survey material lives in
`scratchpad/yolo_survey/` (scripts, torch weights, 9-frame eval set, crop sheets, live evidence).

**Eval set:** 9 real-phone frames, native 2392x1080 — 6 distinct enemy bases (one in a lava skin,
one mid-battle) + own village at 3 zooms (`scratchpad/yolo_survey/eval/`). Graded by cropping EVERY
box, never by count, then re-graded blind by a separate agent: identical verdicts at conf >= 0.80.

| model (source)                                   | loads       | verdict on our frames                                                             |
| ------------------------------------------------ | ----------- | --------------------------------------------------------------------------------- |
| **BurntBaseTeam YOLOv5s, 26 cls (GitHub, 2023)** | yolov5 repo | **usable for defences at conf >= 0.80** — see below                               |
| Sandeep/Shriyam YOLO11n, 27 cls (GitHub, 2025)   | ultralytics | REJECTED: boxes land on buildings, labels wrong (storage→cannon 0.93)             |
| Bulatypov YOLO11n, 22 cls (GitHub, 2024)         | ultralytics | REJECTED: 9-14 "town_hall" per frame; builder huts as TH                          |
| keremberke YOLOv5 n/s/m, 16 cls (HF, 2022)       | yolov5 repo | not graded: TH13-only training set, 640 px: 4-8 "ad" per frame, 1280 px: up to 12 |
| nick troops / area, nihat deploy-seg, phantom UI | ultralytics | not building detectors (troops, deploy area, UI buttons) — untested               |

**BurntBaseTeam YOLOv5s (`weights/burnt_yolov5s_26cls.pt`, sha256 175fc151…) at conf >= 0.80:**

| class   | imgsz | precision                             | recall                           |
| ------- | ----- | ------------------------------------- | -------------------------------- |
| air_def | 800   | **27/27 (100%)**                      | **27/30 (90%)**                  |
| air_def | 640   | 28/29 (97%)                           | 28/30 (93%) — FP a banner        |
| inferno | 640   | 24/24 (100%)                          | not measured                     |
| inferno | 800   | 24/25 (96%) — FP a burning Bomb Tower | 24/27 (3 per frame, all visible) |
| xbow    | 640   | 23/23 (100%)                          | not measured                     |
| xbow    | 800   | 23/23 (100%)                          | 23 of 31 pooled-known            |
| eagle   | 640   | 6/6                                   | not measured                     |
| scatter | 640   | 4/4                                   | not measured                     |
| th      | 640   | 6/9 (67%)                             | UNUSABLE — pre-TH16 art          |

Latency, M4, median of 90 (9 frames x 10), letterbox+infer+NMS:
`python3 v5time.py weights/… mps 800` → **22.8 ms MPS** (p90 26.1), 128.8 ms CPU; imgsz 640 →
18.0 ms MPS, 83.4 ms CPU. vs `locate.py` VLM ~21 s + ~$0.01/frame at 100%/90% on air_def.

- **Below 0.80 it is junk:** 36 of 50 sub-0.80 tiles were FALSE — banners on poles, hero cards,
  the "Battle starts in" countdown, UI buttons. The threshold is load-bearing.
- **Misses are cosmetic skins.** 2 of the 3 air_def misses are the LAVA-skin base (true ADs at
  0.73 / 0.59); the third is a partial AD at 0.73. Skins postdate the 2023 training data.
- **It has no class for Monolith, Spell Tower, Multi-Archer Tower, Ricochet Cannon, Firespitter**, and
  `th` is wrong on modern Town Halls. It cannot replace `locate.py` for those.
- **License: the source repo has NO license.** Fine for this private account; do not redistribute.
- Loading needs the cloned yolov5 repo (commit 402e17dd) AND an isolated import path: the system
  Python has `_invoice_mcp.pth` (another project's yolov5) plus a stray `utils` package in
  site-packages, both of which shadow the repo. `v5load.py` strips them in-process; nothing global
  was modified.
- **LIVE VERIFIED 2026-09-17** on the phone (Home Village in front, battery 36% charging):
  `coc.capture.ScreencapSource.grab()` → `v5live.py live1.png 800` → 24.6 ms median (n=20). At
  conf >= 0.80: air_def 4/4, xbow 4/4, air_sweeper 2/2, th 1/1 all correct (TH15 maxima: 4/4/2/1);
  inferno 2 of 3 (third at 0.75), eagle found at 0.68, **scattershot 0 of 2 detected**, 0 false
  positives. Evidence: `scratchpad/yolo_survey/live_20260917/`.
- **The frame grab is now the bottleneck, not perception:** `screencap` took 8,088 ms for that
  frame vs 25 ms to detect. See "Faster frames for battles" below.

Public datasets downloaded for a future fine-tune (session scratchpad, not copied):
Kaggle `kush1203/clash-of-clan-objectitem-detection` (800 imgs, 35 cls TH4-16, 640 px crops of
watermarked guide images, sparse labels) and HF `PranjalSeluriyal/Pranjal-ClashOfClan-yolo11`
(68 imgs, 45 cls TH14-17 phone attack view, densely labelled but heavily rotation-augmented).

## ACCOUNT + GAME KNOWLEDGE (2026-09-17)

- **The account is TH15, not TH14.** The 2026-09-15 battle bar (native crop of `a4/view_0`) shows a
  **Dragon Duke L2**, and the wiki Hero Hall table unlocks Dragon Duke at Hero Hall 9 = **TH15**.
  Army camp 300 and Lightning L9 (the TH14 lab cap) mean TH15 upgrades are unfinished. Not yet
  confirmed from the in-game Town Hall label.
- Heroes seen: Grand Warden 56, Dragon Duke 2, Minion Prince 49, Barbarian King 49 (2026-09-15);
  Royal Champion 27 and Archer Queen 83 in the 2026-09-12 army. Live HUD 2026-09-17: XP 189,
  gold 13,208,064, elixir 4,827,532, dark 25,824, gems 898.
- **Lightning count per Air Defense (wiki arithmetic, L9 = 560 dmg):** ceil(HP/560) → 3 vs AD L12
  (1,650, TH14 max) and below, **4 vs AD L13+ (1,750, TH15 max)**. So 11 Lightning takes out
  only **2** maxed TH15+ ADs (3 left over), not 3. Read the defender's TH before dropping.
- Loot (regular/"Casual" Battles): storages 14% capped at 1.54M per resource at TH15 (DE 5%,
  cap 9,250); collectors 50%, drills 75%, uncapped; TH-difference multiplier 5%-200% — **skip bases
  2+ TH below unless collectors are full** (50% / 25% / 5%).
- Hero abilities **auto-fire on KO by default** ("Automatically use Hero Abilities on KO"), and the
  Barbarian King auto-fires at battle end. "Fire each ability exactly once" must check the icon is
  unused before tapping, or the setting must be turned off.
- Seeking Air Mines trigger only on air units of 5+ housing (Dragons, Baby Dragons, Healers, Minion
  Prince). Air Sweepers clump Baby Dragons, cancelling their solo rage bonus.
- **Lightning (wiki, pasted by the owner 2026-09-17):** ONE bolt per spell, 2-tile radius (21 tiles
  if dropped on a tile centre), stuns briefly; L9 560 / L10 600 / L11 640 / L12 680 / L13 720; no damage
  to storages, Town Hall, Clan Castle. Can damage several buildings at once when close together.
  At battle zoom a tile is ~25-33 px, so the radius is ~50-65 px. Observed (a11): an AD 88 px from
  two 4-bolt zaps died, one 88 px from a single 4-bolt zap survived.
- **When a troop card runs out, the game auto-selects the next card with charges** (a11, a13: Lightning
  selected with no Lightning card tap). Any map tap then casts it.
- **The selected card has a thick white border** (graded on 156 frames); `autoloop2.card_selected()`'s
  raised-band test is wrong in battle.
- **Tag Team Equipment Blast event (Sept 9-22, 2026):** "Pick a Reward!" at 33/66/100% destruction dims
  the battle, freezes the timer for ~10 s (countdown bar under the ribbon) and auto-picks Gold.
- **Camera limits differ per base**: a9/a10 x +630/-643, a11 +366/-245, a12-a15 ≈ +319/-292.
- The owner sometimes plays along by hand during a battle (picked rewards, panned, cast in a11/a13).
- Knowledge base: `scratchpad/knowledge/hv_defences.json` (23 defences + 8 traps, targets / range /
  count at TH14-16 / source URL; visual descriptions are paraphrased wiki text, NOT checked against
  frames) and `scratchpad/knowledge/doctrine.md` (each claim tagged CONFIRMED or COMMUNITY).

## Next

- [x] **Land the YOLOv5s detector as locate stage 0** (2026-09-17) — see "LOCATE STAGE 0 LANDED".
- [ ] **Scattershot is unresolved.** The detector found 0 on the live own village, its low-conf
      "scatter" boxes were an X-Bow, a cannon and an archer tower, and I could not find the two
      Scattershots by eye in that frame either. Not exposed; tap one to get its name before grading.
- [x] **Deploy targeting is MODEL ONLY** (owner's decision 2026-09-17). New
      `locate.deploy_targets(frame)` = stage 0 at conf >= 0.80, never the VLM, refuses ungraded
      classes. Measured: identical output to the graded `--no-verify` run on 9/9 frames (74/75
      true), 84.1 ms median, 0 VLM calls; saved live enemy frame 10 targets, 0 calls; **LIVE grab
      on the phone** (Home Village, battery 40%): 8.9 s grab + 104 ms, 8 targets, **8/8 true by eye**
      (AD 4/4, X-Bow 3, Inferno 1), 0 VLM calls — missed 1 X-Bow and 2 Infernos below the line.
      Tests 14 passed; `test_deploy_targets_are_model_only` fails if `verify=True` is restored.
- [x] **Attack scripts switched to `deploy_targets()`** (2026-09-17; `attack5/6/7.py` in the
      2026-09-15 session scratchpad `/private/tmp/claude-502/…/bddbef9d-…/scratchpad/`, backups in
      the 2026-09-17 session scratchpad `attack_backup/`). **The swap was not cosmetic:** all three
      filtered `if d.verified`, and since stage 0 landed that filter KEPT only VLM-confirmed
      review-band boxes and DROPPED every model box >= 0.80 — on the 9 graded frames it kept 4 ADs
      (1 false) and dropped all 27 true ones. A bare swap would have dropped everything (model-only
      boxes are never `verified`), so the filter was removed. The 840 px HUD cut-off and
      AD_MIN_Y are unchanged. Checked: `py_compile` OK; `deploy_targets(frame, ("air_defense",))` on
      the 11 panned views those scripts captured (a4/a5/a8 views, p1 prep) → **21 targets, 21/21
      true Air Defenses by eye** (incl. 2 lava-skin), 195 ms median, 0 VLM calls. NOT run in a live
      battle.
- [x] **Attack scripts preserved in the repo** (2026-09-17): `scratchpad/attack5.py`,
      `attack6.py`, `attack7.py` plus the modules only they needed — `camera.py`, `strategy.py`,
      `recorder.py` — and the card templates `scratchpad/cards/` (9 PNG + `lightning_bar.webp`).
      16 files, sha256-identical to the /private/tmp originals, nothing overwritten. Checked from
      the repo copy: all compile; `autoloop2`, `match`, `camera`, `strategy`, `recorder` import from
      `scratchpad/`; every card template loads. Run from `scratchpad/` with `PYTHONPATH=<repo>`.
      Then also `attack1.py`-`attack4.py`, `deploy_plan.py`, `enter_scout.py`, `probe_shade.py` (7
      files, sha256-identical, no collisions): all compile, their local imports (`autoloop2`,
      `match`, `waves`) resolve from `scratchpad/`, and every card template attack1-4 reference loads.
      None of the seven call the building locator, so no targeting change applied. Every script from
      the 2026-09-15 session is now in the repo; its 5 wiki `.txt` page dumps were not copied.
- [ ] **Fine-tune for the missing classes and skins** — label our own frames (VLM staged locate +
      crop review) plus the two public datasets; target Monolith, Spell Tower, TH15-17, skins.
- [ ] Fix `locate --json --overlay` writing a non-JSON line to stdout (found 2026-09-17).
- [ ] **Verify AD midpoint pairing live** — needs a base with ADs within 100 px (a11/a14 layouts).
      Judge by both ADs falling after the midpoint bolts (`rec.json` zaps `standing_after`) and the
      result screen's Lightning count.
- [ ] **Verify the selected-card guard fires live** (`wrong_card` event) — only happens if something
      else selects Lightning mid-deploy; the replay covers it (`--switch-at`), a battle has not.
- [ ] **AD recall on non-green sceneries**: a15 found 2 (likely 4), a9 found 0 live. Fine-tuning (below)
      is the fix; until then spare bolts land on rubble there.
- [ ] Spare bolts are pure waste when few ADs are found (a15: 5 on rubble). Owner accepted it to leave
      nothing castable; revisit if a spell-safe alternative appears.
- [ ] Land the attack system into `coc/flows/` (Tapper + battle-scoped no-tap zones) — it still runs
      from `scratchpad/`. `autoloop2.py` is 991 LOC (over the 600 cap).
- [ ] `attack5.py` / `attack6.py` still use the old green-only spot finder and none of the a10-a14
      fixes; do not run them.
- [ ] Confirm TH15 from the in-game Town Hall label (one navigation tap on the TH).

- [ ] **Boat / Clan Capital need templates, not coordinates.** Unlike the HUD,
      world objects move with the camera, so no fixed tap point is valid.
      Cut `boat_builder_base` and `clan_capital` templates and match them.

- [ ] **`NO_TAP_ZONES` "Upgrade suggestion" (2150,425,2392,520) is still an
      estimate.** That button only renders when a builder is free; at 0/7
      it could not be measured, so the zone currently lies over open
      village and will refuse a bubble there. Capture a frame with a free
      builder, measure it, and tighten -- or replace it with a template
      match so it only applies when the button is actually present.
- [ ] **Identify the bottom-left button at (331,870)-(479,1054)** -- silver
      shield + medical cross, "22d 15h", "2x" over a green elixir drop.
      Protected as a no-tap zone until known.
- [ ] **Load the launchd agent** — written but deliberately NOT loaded.
      `launchctl bootstrap gui/$(id -u) scripts/com.arnab.coc-collect.plist`
- [x] Builder Base (2026-09-09): boat located and tapped, layout mapped, three
      bubbles collected, one live attack run. See "Builder Base" below.
- [ ] **BUG (found, NOT fixed): `find_loot_bubbles` matches nothing at its own
      threshold.** `find_all(frame,"loot_bubble",0.15)` returned 0 matches on
      every frame tested including a Home Village frame with two visible dark
      elixir bubbles. The shipped template is 85x82 but the bubble renders ~52
      px wide at the zoom levels observed — bubbles scale with camera zoom, so
      the single-scale template only matches at the zoom it was cut at (best
      min score 0.1228 at scale 0.90, still no match at scale 1.0). This is the
      likely root cause of the logged "collect reported 0 bubbles while bubbles
      were visible". `builder_base.find_bubbles()` is zoom-tolerant and found
      them; porting it to the Home Village flow is untried.
- [ ] Validate `assets/templates/boat_builder_base.png` on a SECOND pan. It was
      cut from the frame it was found in, so it has no independent evidence.
- [ ] BB trophies fell 3441 -> 3417 while the reward panel said +12. A defence
      loss while attacking is the suspicion (a red "1" badge appeared on the
      left rail), but it was never observed directly.
- [ ] Free claimables: Star Bonus, Builder Base bonus, Trader free item.
- [ ] Tier-3 OpenRouter fallback (`coc/vision/vlm.py`) — classify unknown
      screens and write the answer back as a template. Model is chosen
      (`google/gemini-3-flash-preview`); the module is not written yet.
- [x] Attacks — farm **Casual**, not Ranked (Ranked has a weekly allowance
      and a sign-up deadline; Casual is unlimited). Extensive live research
      is recorded under **## Attack research** below; read it before
      resuming — several plausible approaches are already disproven there.
      **Working as of 2026-09-10**: 10 matches, +10,716,752 gold, 10/10 clean.
      See **## HOME VILLAGE FARMING SESSION 2026-09-10**. Deploy points are a
      solved problem (green-grass complement). Code is saved in `scratchpad/`
      (see the index below); it is NOT landed in `coc/` and has not been through
      the `coc/` contracts or the verification gate.
- [ ] **Land the battle runner into `coc/flows/`** as `attack_home.py` +
      `cmd_attack` in `cli.py`. Source is `scratchpad/autoloop2.py` +
      `scratchpad/waves.py` (saved, no longer at risk of being lost). What must
      come with it, all measured this session: - `prep_active()` — deploys DO NOT register during the prep countdown,
      and `battle.in_battle()` cannot tell prep from a live battle; - `card_alive()` — the grey-card test, 55/55 on labelled states; - `Budget` + `Spread` — hard caps on taps and on taps-per-cell; - `calibrate_bar()` — ticks 1:1 with cards (PITCH 143.9 is a constant); - `loot_side()` — attack the side the storages are on, not the biggest; - BACK-only `to_village()` and the tight Return-Home box.
      **`battle.CARD_X` is WRONG** (the bar is centred) — delete it or mark it
      unsafe. `NO_TAP_ZONES` must become screen-scoped before any of this ships,
      since in a battle they cover the troop bar.
- [ ] **The ~16-run loot comparison.** Everything this session is verified
      mechanically (taps, stacking, aim) but NOT on gold. Per-match gold ranged
      121,870-1,983,433 on the blind runner, so n=1 comparisons are meaningless;
      ~16 runs per arm are needed to resolve even a 20-point effect.
- [ ] Faster frames for battles. `exec-out screenrecord` hangs on this device
      and scrcpy 3.3.4 dropped raw-h264-to-stdout, so this needs speaking the
      scrcpy server protocol directly.

## a9 (2026-09-17, attack7.py + deploy_targets) FAILED: -1,400 g, 0 units, 0 Lightning

Command: `cd scratchpad && PYTHONPATH=<repo> python3 -u attack7.py scratchpad/battles/a9_20260917`
(battery 29% discharging, user hands-off). Evidence in `scratchpad/battles/a9_20260917/`
(rec.json, console.log, 5 scan views, 25 recorder frames, `a9_diag.py`, `a9_mid/up.webp`).

- **What worked: the a8 camera fix, first live run.** Every pan measured or relocalized: up +491
  (9/10), down -484 (6/6), a failed diagonal pan relocalized to `mid` (11/14). Cards located
  0.905-1.0. Recorder 25 frames, 0 failures. Gold -1,400 exactly (search fee only).
- **What failed:** `locate` = 0 ADs on all 5 views -> plan "no AD found", 0 zaps; then
  `find_spot` returned with **probes 0** -> dragons skipped -> nothing deployed, no heroes, no
  abilities; the review loop idled until `battle_over` at T+130.7 s. "Fail-closed never means do
  nothing for 3 minutes" was violated again: there is no deploy fallback when no spot is found.

Root causes, reproduced offline (`a9_diag.py`) and then attacked by a fresh red-team agent
(scripts in the 2026-09-17 session scratchpad `redteam/`):

1. **The enemy base uses a BLUE underwater scenery.** Defender sceneries show in attacks.
   RED-TEAM: **CONFIRMED.** All 260 grid points die at the eroded mask on all 5 views and all 25
   battle frames (not at the HUD/refused/cam filters); a4/a5 green views keep 24-102 points under
   the same 31x31 erode, so the kernel is not the culprit; JPEG adds points rather than hiding them.
   Recolouring 8 green frames toward blue keeps only 4 of 23 ADs >= 0.80 (desaturating keeps all
   23); recolouring a9 toward green lifts its true ADs to 0.816-0.879. 4 distinct ADs WERE in view.
   Unexplained: `left`'s AD scores 0.81 on the saved JPEG but live returned 0 (raw likely <0.80).
   - `find_spot` -> `grid_candidates` needs green grass: `green_mask` 129-145k px, but after the
     31x31 erode **0-326 px, 0 of 260 grid points** on the first 6 battle frames -> 0 probes.
   - The YOLO model (trained on green bases) loses AD confidence: sequential `deploy_targets` on
     the 5 saved views = **1 AD total** (left). In `up` a true AD scored **0.79** (below the line);
     in `mid` a clearly visible AD at ~(560,385)/1800-scale was **not boxed at all**. X-Bows and
     Infernos mostly still >= 0.80 (mid: xbow 0.89/0.82, inferno 0.87/0.81).
2. **`yolo.detect` is not thread-safe.** `attack7.scan_map` runs `deploy_targets` in 5 threads;
   they share one `cv2.dnn.Net`. Reproduced: 5 concurrent calls on 5 different views return the
   SAME count every time (37/37/37/37/37, then 115x5, then 27x5) — outputs overwrite each other.
   RED-TEAM: bug **CONFIRMED** (raw net from 5 threads: 0/5 match sequential in 5 repeats; 5/5 with
   a lock), but as a9's cause **WEAKENED**: live, each scan thread started >= 1.3 s after the last
   (a pan between views) against a 0.17-0.30 s pass, so they almost certainly never overlapped.
   A latent bug for any threaded caller, not what emptied a9. My "Live it returned 0x5" framing
   above overstated it. Side finding: the old skip text "every spot refused" was false at probes=0.

### a9 fixes (2026-09-17, user-approved "first three") — offline re-test, NOT run in a battle

1. **Thread-safe detector.** `coc/vision/yolo.py`: a module lock around setInput/forward.
   `tests/test_yolo.py::test_concurrent_detect_matches_sequential` (4 threads x 2 frames) —
   `pytest tests/ -q` **15 passed**; with the lock removed the test failed 3/3 runs. On a9's 5 views,
   5 simultaneous-thread repeats: **0 of 25 results differed** from sequential.
2. **Never idle.** New `scratchpad/spots.py` (pulled out of attack7 to be testable): grass points,
   then a colour-free ring of screen points (3 ellipses, 15 deg steps); `probe()` taps until the game
   accepts, budget `MAX_REFUSED + RING_PROBES` = 16, re-checks the refusal radius before each tap.
   `attack7.find_spot` uses it; the review loop retries up to `DEPLOY_RETRIES = 2` times while no
   spot has been accepted and dragons are still in hand (then batches 14 more + support).
3. **Scenery detection.** `spots.GREEN_MIN_PX = 40,000` eroded-grass px. Measured: 46 green-base
   frames min **57,928**; 30 a9 blue frames max **24,680**. Below the line the grass grid is skipped.
   `scratchpad/test_spots.py` (run from `scratchpad/`, `PYTHONPATH=..`): **49 passed** — green eval
   bases read as grass AND their grass candidates are identical to the pre-a9 `grid_candidates`;
   all 30 a9 frames read as non-grass with >= 16 ring points; probes are bounded, never re-tap, and
   a retry offers only new points. Mutations each caught: no scenery detection 9 failed, ring
   removed 36 failed, refusals forgotten 8 failed, budget ignored 8 failed.

**Open — the ring is NOT known to deploy on a9-like views.** Plotted on a9 (`ring_*.webp` in the
battle dir): on the zoomed landing/battle view nearly all of the first 16 ring points sit INSIDE the
base (walls, buildings), so the game would likely refuse them and the 16 + 2x16 probes (~2 s each)
could burn ~90 s and still place nothing. On the `up` scan view the outer-ring points farthest from
centre (8, 12-16) land on open floor outside the faint red deploy line.

### Edge view + far-first ring (2026-09-17, user-approved) — offline re-test, NOT run in a battle

- **Far-first ring:** `spots.ring_candidates` now orders each ellipse FARTHEST from the view centre
  first (was nearest-to-`near`). Plotted (`far_up.webp`, `far_down.webp` in the battle dir), graded by
  eye: on both a9 edge views probes 1-5 sit on open floor outside the red deploy line; the in-base
  points moved to the end (13-16). Eye-grading, not game truth.
- **Edge view:** on a non-grass scenery `attack7` pans to an up/down scan view (`spots.edge_views`,
  anchor side first, only captured views) BEFORE tapping the dragon card; each review-loop retry
  moves to a not-yet-probed edge view first. In a retry the dragon card is usually still selected
  from the opening — p1 measured a selected-card pan as safe (n=1) and the swipe starts mid-base.
- Tests: `test_spots.py` **51 passed** (+ far-first order, + edge-view choice); `pytest tests/ -q`
  **15 passed**.
- **Offline replay of the real `attack7.py`** (`scratchpad/replay_attack7.py`: fake device, clock,
  camera and game over a9's 5 saved views; the fake game accepts a dragon only within 60 px of 7
  floor points graded outside the deploy line on `up`). Run from `scratchpad/`,
  `PYTHONPATH=.. python3 replay_attack7.py battles/replay_a9 [--no-edge]`:

  | run                       | edge view      | first dragon accepted      | dragons | support + abilities               | opening done                |
  | ------------------------- | -------------- | -------------------------- | ------- | --------------------------------- | --------------------------- |
  | **new**                   | `up` at 21.8 s | probe 1 (2276,485), 26.6 s | 15/15   | hog, log, 4 heroes; 4/4 abilities | 29.9 s                      |
  | control `--no-edge` (old) | none           | never: 3x16 = 48 refused   | 0/15    | none                              | 59.2 s, probing until 145 s |

  Both: 0 probe re-taps within 45 px; 5 Lightning cast on the 1 AD from the `left` view. The first
  replay run was wrong because the FAKE badge ignored which frame it was read from (accepted taps
  looked refused) — fixed in the harness, not in attack7. The replay proves order and bounds; whether
  the real game accepts probe 1 is still only settled by a live non-green battle.

### a10 LIVE (2026-09-17): DEFEAT, 0 stars, 26% — the clock ran out before the army went in

`battles/a10_20260917/` (rec.json, console.log, 37 recorder frames). GREEN base (green_px 258,762),
so the new ring/edge-view code never ran. Loot +172,087 g / +437,647 e / +5,208 d. Result screen:
Dragon x5, Hog, Log, 4 heroes, **Lightning x9 (card level 9 = 560 dmg)**. 4 ADs found (mid 4, up 2).

User report (verified): "4 lightning on a lvl 12 AD, it takes 3" and "~2 minutes dropping thunder".

Battle clock, read from the timer in the recorder frames (attack7 t0 ~ recorder 68 s):

| clock left   | what happened                                                                     |
| ------------ | --------------------------------------------------------------------------------- |
| 3:00 → 1:55  | 5-view scan still running (prep had 10 s left when the recorder started)          |
| 1:55 → ~0:30 | 9 Lightning in 3 stops (4 + 4 + 1); 8 cast by 0:37                                |
| ~0:25 → 0:15 | first dragon (5 probes, "cannot deploy on red area"), only 5 of 8 landed; support |
| 0:15 → 0:00  | group-2 pan + relocalize — battle ended inside it                                 |
| after end    | **16 "refused" group-2 probes were taps on the DEFEAT screen**; no ability fired  |

Root causes — red-teamed by two fresh agents, then FIXED (see "a10 fixes" below):

1. **Every diagonal pan runs `camera.relocalize` (~17 s offline, ~25-30 s live).**
   `_patch_centres` puts all diagonal-drag patches inside `HUD_BOXES`: 0 usable patches for all 4
   a10 diagonal drags (checked offline), so `scene_shift` returns n=0 by construction (4/4 diagonal
   pans failed live, 0/15 axis pans). 4 relocalizes ≈ 100 s of the 180 s clock. Offline:
   `relocalize(t0101.6, a10 views)` 16.9 s / 16.1 s, same cam (-316,450) as live. CONFIRMED (red
   team: no diagonal drag of any size keeps a patch; 5/5 live diagonal pans a9+a10 had n=0;
   relocalize 14.3 s offline = 165 matchTemplate x 0.086 s; live event gaps imply ~29-34 s).
2. **`to_cam` repeats pushes past the MAP EDGE that move the camera 0 px** (7/7 in the scan), up to
   `max_steps` — ~3 s each, ~24 s. My first reading ("small drags have a dead zone") was FALSIFIED
   by the red team: a9 and a10 both stopped at x +628..+631 / -640..-643 from different starts,
   large drags into the edge fell short (0.79-0.83 of expected vs 0.90-1.12 elsewhere), and a
   144 px drag near the centre moved 164 px. a11 then moved 111 px for a 106 px drag mid-map.
3. **Lightning is verified one by one**: tap, 0.45 s, full screenshot, badge read, per spell —
   ~1.4 s x 9 (red team: a grab is <= ~1.0 s, not 1.3). Worse: the badge crop CANNOT see the
   lightning count change (badge_delta 0.57 / 0.69 vs BADGE_MOVED 4.0), so zap 3 stopped after 1.
4. **`strategy.LIGHTNING_PER_AD = 4`** still carries the old "~480 (UNVERIFIED)" note; doctrine.md
   already says L12 AD 1,650 / 560 → 3 (1,680). AD3 got 1 spell (useless), 2 spells left unused,
   AD4 never planned. Caveat: a maxed TH15 AD (L13, 1,750) needs 4 at L9.
5. **`find_spot` never checks `in_battle`** — it tapped the result screen 16 times (harmless this
   time, but it is acting on a screen it did not name).
6. Zap 3 logged cast=0 but the game counted the spell (badge blind to the count, item 3).
7. Group 1 queued 8 dragons, 5 landed (x14 → x10 in frames); cause UNDECIDED — red zone or dropped
   taps in the fast 7-tap chain. Not fixed.

### a10 fixes (2026-09-17, user-approved "make the fixes and re-test")

Pre-fix copies: `scratchpad/battles/a10_20260917/pre_fix/`. Changes:

- `strategy.py`: `LIGHTNING_PER_AD = 3`, whole kills only (a 4-AD base with 11 spells → 3+3+3, 2 in
  `lightning_reserve`); the reserve is ONE extra bolt on an AD still standing after its 3.
- `attack7.py`:
  - `to_cam` pans ONE axis at a time (larger error first); an axis whose pan moved < 50% of expected
    is marked at the map edge (`map_edge` event) and not retried. Scan targets ±620 (was ±760).
  - `bring_into_view`: an AD already inside x 300-2090 / y 250-730 is zapped without panning.
  - Zaps: all bolts for an AD in ONE `input tap` chain, 1.5 s settle, one screenshot, then
    `ad_standing()` (model: AD box >= 0.80 within `STANDING_PX` of the aim point) decides the top-up.
    Graded on a10 frames: standing 0.89-0.90 (22 crops), rubble / mid-explosion 0.00 (8) — 4 ADs.
  - `in_battle()` is checked before every tap sequence: zap loop (before AND after the pan), card
    taps, group loop (before and after positioning), support, each probe (a probe after the end is
    not recorded as a refusal), review-loop retry.
- New `scratchpad/replay_a10.py`: the real attack7 on a10's views with a10's MEASURED costs on a fake
  clock (relocalize 30 s, grab 1.0 s, tap 0.08 s; camera clamped at a10's edges; 4 ADs with HP and
  560-dmg bolts; deploy legal outside a diamond graded from a10's live taps — it reproduces the live
  accepted probe, 3/4 refused probes and 5 of 8 dragons). Frames are shifted to the camera offset
  (the first version was not, and an AD 275 px from its aim point read as destroyed).
  **Calibration, pre-fix code vs live a10:** first bolt 1:54 vs ~1:55 left, last bolt 0:33 vs ~0:30,
  first dragon 0:24 vs ~0:22, relocalizes 4 vs 4, edge pans 7 vs 7, taps after end 17 vs 16.

Measured, `PYTHONPATH=.. python3 replay_a10.py OUT [--code battles/a10_20260917/pre_fix] [--ad-hp N]`:

| replay (a10 base)                 | pre-fix L12 | fixed L12 | fixed L13 (1,750 HP)                 |
| --------------------------------- | ----------- | --------- | ------------------------------------ |
| clock left at first bolt          | 1:54        | 2:41      | 2:41                                 |
| clock left at last bolt           | 0:33        | 2:25      | 2:19                                 |
| clock left at first dragon        | 0:21        | 2:11      | 2:05                                 |
| relocalize / diagonal / edge pans | 4 / 4 / 7   | 0 / 0 / 0 | 0 / 0 / 0                            |
| bolts (wasted)                    | 11 (2)      | 9 (0)     | 11 (0): taps 4, 4, 3                 |
| ADs destroyed                     | 3           | 3         | 2 (3rd left at 70 HP, reserve spent) |
| dragons landed                    | 8           | 15        | 15                                   |
| taps after the battle ended       | 17          | 0         | 0                                    |

Battle forced to end early (`--battle-s` 5…180, 16 cutoffs): fixed code 0 taps after the end at
every cutoff; pre-fix 38 at 25 s and 50 s (the first fixed version still sent 3 bolts and 1 card
tap after the end — the check ran before a ~3 s pan; moved to after it).

Tests: new `scratchpad/test_battle_clock.py` **11 passed** (strategy allocation x5, a10 clock+bolts,
L13 top-up, no taps after end x4). Mutation: pre-fix attack7 → 6/6 replay tests FAIL;
`LIGHTNING_PER_AD = 4` → 7 FAIL. `test_spots.py` 51 passed; `pytest tests/ -q` 15 passed. a9 replay
(non-green path) unchanged in outcome: 15 dragons, edge view `up`, first accepted probe 1; on the
t0 clock edge view 16.2 s (was 21.8), accepted 21.1 s (was 26.6). (Its "19 retaps within 45 px" are
top-up batch taps, identical before the fix — the earlier "0 probe re-taps" line counted probes only.)

### a11 LIVE (2026-09-17, fixed code): VICTORY, 3 stars, 100% — +827,155 g / +482,014 e / +10,705 d

`battles/a11_20260917/`. Army checked full first (My Army panel: heroes 4/4, 305/305, spells 11/11).
Green base; this map's camera stopped at x +366 / -245 (not ±630): `map_edge` fired once per side.
Storage delta +1,085,755 g / +742,014 e / +12,405 d.

| clock left (recorder timer)         | a10 (pre-fix, live)  | a11 (fixed, live)     |
| ----------------------------------- | -------------------- | --------------------- |
| first bolts                         | ~1:55                | between 2:29 and 2:23 |
| planned bolts done                  | ~0:30                | by 2:16               |
| first dragons                       | ~0:22                | between 2:16 and 2:09 |
| both groups + support + 4 abilities | never (group 2 lost) | by ~2:01 (t0+35.8)    |
| relocalize / edge pans              | 4 / 7                | 1 (scan) / 2          |

Different bases, so the result (Defeat 26% → Victory 100%) is not a controlled comparison; the
clock numbers are the fix. The in-battle guard was NOT exercised live (the battle ended at 100%).

**Problems found in a11 — reported, NOT fixed (awaiting the user):**

1. **Top-up bolts wasted on destroyed ADs (2 of 8).** Both zaps logged `taps 4, standing_after true`.
   Frames: at both aim points the AD was rubble/exploding after 3 bolts, but ANOTHER AD box sat
   87-88 px away (a tight AD cluster) — inside `STANDING_PX = 90`. The live aim-to-box offset on a
   standing AD was 2 px. Proposed: `STANDING_PX` ~40.
2. **`DEDUPE_PX = 90` merged neighbouring ADs** (pre-existing): the up view had 4 AD boxes, the plan
   got 2 world ADs, so the cluster's other ADs were never targeted. Proposed: no dedupe inside one
   view; a smaller cross-view radius after measuring the cross-view world error.
3. **Lightning cast OFF the ADs — breaks the user rule.** Result screen: Lightning x11 used; the script
   tapped 8 (all on AD aim points). Card bar in frames: x3 at 72.8 s → x2 at 82.2 → x1 at 89.3-109.1
   → x0 at 117.5; Lightning shown SELECTED after the dragons hit x0. The dragon top-up at t0+35.8
   (≈ recorder 74) tapped `batch_near(p, 6)` with only 3 dragons left, and the game auto-selects the
   next card with charges — that fits the x3→x2 cast. **The x2→x1 and x1→x0 casts (≈ t0+44-51 and
   t0+71-80) have NO tap from attack7** (Device.shell is synchronous; no other process, no launchd
   job, runs.jsonl untouched since 09-10). A "Pick a Reward" event popup was up at 82.2. ROOT CAUSE
   NOT FOUND for those two. Proposed guard: map taps only while `al.card_selected(frame, card_x)`
   is true for the intended card, and top-ups one tap at a time.
4. **One relocalize remained, in the scan:** an axis pan (finger -600) ran into the map edge mid-drag;
   the scene moved -611 of an expected -762 and 0 of 6 patches agreed, so the measurement failed.

### a11 fixes (2026-09-17, user-approved "fix all four and re-test")

Pre-fix copies: `scratchpad/battles/a11_20260917/pre_fix/`. Red-teamed by two fresh agents first.

1. **Lightning off the ADs.** CONFIRMED part: the top-up tapped 6 with 3 dragons left and the game
   auto-selects the next card with charges (Lightning selected at 89.3-109.1 with ONE Lightning
   card tap, in the zap phase). The other 2 casts: no attack7 tap or swipe after t0+35.8 (red team
   read every path; Device.shell has no retry), and the camera moved by itself several times,
   following the dragons, during the same window. ROOT CAUSE NOT FOUND: an event mechanic (Tag Team
   Equipment Blast, Sept 9-22: picks at 33/66/100%) or a person touching the phone — the frames
   cannot separate them. `card_selected()` is unusable in battle (reads 4-6 cards selected).
   Fix: `tap_units()` — dragons ONE per tap, each after a fresh `card_alive()` check; probes stop
   when the card is out; every tap journaled in `rec["taps"]`; a half-size review frame per loop
   iteration (`review/`) and a `lightning_card` event when the card greys.
2. **Top-up on rubble.** CONFIRMED (both aimed ADs were rubble; neighbours 87/88 px away were the
   standing boxes; aim error 2 px). Fix: `STANDING_PX` 90 → 40 and a box must be nearest to THIS AD
   among the known ADs. Aim-to-box error measured 1-7 px on a10/a11 frames.
3. **ADs merged.** CONFIRMED (4 real ADs in a line, two skins). Cross-view error is <= 4.1 px after
   the edge filter (the 17-18 px outliers were cut-off boxes). Fix: `targets.py` (extracted from
   attack7 for the 600-LOC cap) — never merge two boxes from one view, cross-view radius 45 px.
   Also: one unplanned AD died to SPLASH before its turn (red team), so each AD is checked standing
   BEFORE its bolts too, and bolts a skip saves go to `plan["unzapped"]` ADs.
4. **Scan relocalize.** "Camera still bouncing" FALSIFIED (rigid shifts of the settled frame keep
   4/6; no blur). Static aliasing on the spike field CONFIRMED by reconstruction (2 real + 4 aliased
   patches give exactly the logged dx -670 / dy 44). Fix in `camera.py`: x drags use 7 columns x 3
   rows (21 patches) and axis drags search only a +/-60 px band on the other axis; `relocalize`
   takes `predicted` and stops at the first >= 75% / n >= 10 measurement.

Measured offline:

- `scene_shift`, 45 known-offset frame pairs from a9-a11 x 4 (clean + 3 noise/JPEG q55): pre-fix
  163/180 correct, 0 wrong; fixed 172/180, 0 wrong; 108 s → 52 s of matching.
- `relocalize` on 14 recorder frames with known cams x (right guess, worst guess, no guess): same
  camera as the full search 42/42; 1.3 s on 11/14 with the right guess (full: 14.0-14.9 s).
- `replay_a10.py` now models auto-select, splash (full <= 70 px, half <= 100 px, fitted to a11) and
  `--scenario cluster` / `--dragons N`. a11 code → fixed: short army (10 dragons) bolts off the ADs
  2 → 0; cluster: ADs planned 2 → 4, top-ups on rubble 2 → 0, all 4 down both ways. Known limit: the
  3rd bolt of a volley on an AD already weakened by splash can land on rubble (1 in the cluster run).
- Cost of one dragon per tap (a10 replay): support 2:08 → 1:59 left, last dragon 1:59 → 1:43.
- Tests: `test_battle_clock.py` **16 passed** (+ merge on measured a10/a11 coords and a split-view
  case, x pan over a11's spike field on real frames, relocalize with a wrong guess, short army,
  cluster). Mutations all FAIL: a11 attack7 (2 replay tests), pre-fix camera (spike test reproduces
  a11 live: agree 0/6, dx -319), `DEDUPE_PX = 90` (split case 1 != 2), old merge (a11 2 != 4).
  `test_spots.py` 51 passed, `pytest tests/ -q` 15 passed, a9 replay still 15 dragons + 4 abilities.

### a12 LIVE (2026-09-17, a11 fixes): VICTORY, 1 star, 57% — +714,750 g / +521,018 e / +12,917 d (+87% star bonus)

`battles/a12_20260917/` (rec.json with `taps` journal, 28 recorder frames, 117 review frames).
Game was on the inactivity dialog: `ensure_village()` reloaded it; Army panel full before entering.
Storage delta +939,550 g / +747,218 e / +14,396 d. Map edges +319 / -292 (`map_edge` once per side).

- #1 **Lightning x9 used = 9 journaled zap taps**, all on AD aim points; review frames show x2 from
  t67 to the end; the Lightning card never greyed. No off-AD cast.
- #2 3 zaps x 3 taps, `standing_after` false each, 0 top-ups.
- #3 4 ADs planned from 4-4-2-2-4 boxes per view (was the case that merged in a11); 3 zapped (11
  spells = 3 whole kills), 4th in `unzapped`, no bolts saved to spend on it.
- #4 17 pans, 17 measured, 0 relocalize; x pans 21 patches, 8-21 agreeing.
- Clock (recorder timer): bolts 2:37 → ~2:25; first dragon ~2:18; hog/log/heroes ~2:05; group 2
  done ~1:43 (group 2 needed 7 probes). a11: first dragon ~2:12, everything out ~2:01.
- Event popup "Pick a Reward" up at t67-76; the battle TIMER FROZE at 1:42 while it was up; it closed
  with no tap from the script (journal ends at t67.4). The camera did not move by itself (0-5 px over
  117 review frames) and no unexplained cast happened — unlike a11.

**New problem found in a12 (reported, NOT fixed): 5 of 15 dragons stayed in hand for ~110 s.**
Dragon x15 → x10 after group 1 (8 taps) → x5 after group 2 (7 taps): 5 one-per-tap taps landed in
the red zone, and `tap_units` only checks the card has charges, not that the unit landed. The
review-loop top-up then skipped 3 times: it aims at group 1's spot, which was off screen (1832, 73)
from group 2's view. Proposed: check each unit tap for a landing (the screenshot is already taken),
record refusals, and top up at the latest accepted spot that is on screen.

### a13 LIVE (2026-09-17, same code as a12): VICTORY, 2 stars, 87% — +1,984,935 g / +687,539 e / +669 d (+100% star bonus)

`battles/a13_20260917/`. Army panel full, battery 100%. Storage delta +2,243,535 g / +947,539 e.

- 4 ADs, all 3 zaps from the landing view (no pan), 3 taps each, 0 top-ups; 12 pans, 0 relocalize.
- All 15 dragons expended (no red-zone losses this time); support + 4 abilities by t0+59.4.
- Clock (review frame t59.1 read 1:49 with the timer frozen by the event popup): zaps done ~2:38,
  first dragon ~2:26, support ~2:15, group 2 done ~1:50.

**Lightning x11 used, 9 tapped — again — and this time the tap journal is complete.** Last script
tap: t0+59.4 (hero_d ability). Last script swipe: group 2 positioning, before t0+39.8.
Review frames (1 s): t59.1-69.9 "Pick a Reward!" popup (K.A.N.E / Yeti Undertaker / 268,843 Gold),
timer frozen at 1:49; at 69.9 the Gold reward is highlighted (picked); at 70.8 the popup is gone;
the camera then moved by (8,-140) px 71.8→72.9 and (-1,-76) px 72.9→73.8 (scene_shift on review
frames); at 73.8 Lightning x2 shows SELECTED — the game auto-selected it when group 2 spent the
last dragon (~t57); at 74.7 Lightning x0. So a reward pick, two camera moves and two map taps
happened with no input from attack7. Same pattern as a11 (camera following the fight, 2 casts).
Not seen in a12, where the popup closed with no pick visible and the camera never moved.
**User confirmed (2026-09-17): the phone was touched by hand in a11 and a13** — the reward picks,
camera moves and the 2 extra casts were not the script and not the game. The exposure remains that
Lightning stays SELECTED with 2 spare spells after the last dragon, so any map tap casts them.

### a12/a13 fixes (2026-09-17, user-approved: dragon-landing fix + "spend spare 2 on the 4th AD")

Pre-fix copies: `scratchpad/battles/a13_20260917/pre_fix/`. Red team on a12's stuck dragons: counts
CONFIRMED (x15→x10→x5, result 10 used); red-zone refusal PLAUSIBLE (red banner pixels 1.1% vs 0.45%)
but dropped taps not excluded; top-up cause CONFIRMED plus: all 3 top-up attempts fell inside a
"Pick a Reward!" popup (battle paused), within 1.9 s.

- `strategy.py`: whole kills first, the remainder (< 3) on the next AD → 4 ADs: 3+3+3+2, reserve 0.
  With <= 3 ADs found the remainder stays a top-up reserve. Zaps: a partial or extra AD takes what is
  left after later whole kills; top-ups may shrink the partial, never a later whole kill.
- `spots.deploy_units()` (pure, 6 unit tests) + `attack7.deploy_dragons()/place_dragons()`: ONE dragon
  per tap, each checked for a landing like a probe (badge moved or card grey); a non-landing is
  recorded refused and never re-tapped; stops WITHOUT tapping when the card is out, the battle is
  over, or a popup dims the screen; if the ring runs out with dragons in hand, probe once for a new
  spot. Top-ups: every 6 s (max 6), at the newest accepted spot ON SCREEN, else probe the current view.
- `hud.py` (was cardbar.py) `DimGate`: mean V of rows 130-840 < 95 = an overlay; measured on in-battle
  frames a9-a13: popups 74.4-82.9 (37), normal >= 105.1 (280), 2 fade-in frames 80.4 / 93.6. Fails
  open after 20 s of dimming (a dark base must not freeze the attack). No deploy, probe or ability tap
  while it is up; a non-landing under it is not recorded as a refusal. The popup's orange bar is a
  countdown: a13's 66% popup auto-picked Gold at timeout.
- Found while re-testing, fixed: the a11 "standing BEFORE the zap" check skipped a9's only AD — on the
  blue base the model sees that AD from the left view only (0.81) and not at all from mid (no box
  > = 0.25). Rubble at a10/a11 aim points has no box >= 0.25 within 40 px, but no threshold fixes a
  > miss, so the pre-check now runs only within SPLASH_PX 120 of an AD already zapped (a11: 88 px).
- attack7.py 600 LOC (cap): card-bar read moved to hud.py, history docstring trimmed (it is here).

Measured offline (`replay_a10.py`, new `--checker` = patchy red zone, 90 px cells half legal):

| scenario                   | a13 code: landed / in hand | fixed: landed / in hand          | bolts a13 → fixed |
| -------------------------- | -------------------------- | -------------------------------- | ----------------- |
| patchy red zone            | 9 / 6                      | 15 / 0, 0 re-taps                | 9 → 11 (0 off AD) |
| AD cluster                 | 12 / 3                     | 15 / 0                           | 9 → 9             |
| a10                        | 15 / 0                     | 15 / 0                           | 9 → 11, 0 wasted  |
| short army (10)            | 10 / 0                     | 10 / 0, no spill                 | 9 → 11, 0 off AD  |
| a9 non-green (old harness) | —                          | 15 dragons, 3 bolts, 4 abilities | —                 |

Cost: first dragon ~8 s later on a10 (the partial zap on the 4th AD needs a pan); on the patchy base
group 2 ends later (refused taps cost ~1.5 s each).
Tests: `test_battle_clock.py` 17 + `test_spots.py` 57 = **74 passed**; `pytest tests/ -q` 15 passed.
Mutations FAIL as they should: a13 attack7 (a10 bolts 9 != 11; patchy: dragons in hand), a13
strategy (4/5-AD plans), `deploy_units` without landed-point reuse (2 tests).

**Live verification BLOCKED (2026-09-17 ~08:38):** capture came back portrait 1080x2392; foreground
app `in.devhives.sparkle` with a screen recording running — the phone is in use. Nothing tapped.

### a14 LIVE (2026-09-17, a12/a13 fixes): VICTORY, 3 stars, 100% — +613,387 g / +1,954,564 e / +10,601 d (+100% star bonus)

`battles/a14_20260917/`. Army panel full, battery 100%. Storage delta +871,987 g / +2,214,564 e / +12,301 d.

- Plan 3+3+3+2 on 4 ADs in a line ~89 px apart. Zaps 3/3/3 (`standing_after` false); the 4th (between
  zapped ADs) read not standing BEFORE its zap → skipped as designed → 2 Lightning left over.
- **Dragon-landing fix worked live: 15/15 dragons expended, 0 in hand.** Group 1 8/8, group 2 7/7;
  14 dragon taps recorded as refused and never re-tapped; 29 dragon taps in all. 12 pans, 0 relocalize.
- Clock (recorder timer, recorder ≈ t0+24.5): zaps done ~2:38, group 1 + support ~2:06, group 2 ~1:43.

**Lightning x11 used, 9 by zaps — and this time the 2 extra were cast by the SCRIPT's taps.**
Recorder card bar: t0+16.6 dragon card selected (after `card dragon` at t15.28), Lightning x2; t0+25.0
Lightning x2 SELECTED (white border, raised), dragons x13; t0+33.3 Lightning x0, dragons x12. Journal
t15.28-33: probes 16.66/18.18/19.68/21.01(accepted), dragon taps 23.35 (landed), 24.97, 26.34, 27.8,
29.17, 30.53 (all "refused"), 31.86 (landed) — NO card tap. So between t23.35 and t25.0 the selection
moved to Lightning with no input from attack7; the next two dragon taps (24.97, 26.34 at (1000,720) /
(920,720), grass beside the drop spot) cast the 2 spare Lightning and were logged as refusals; the
card then ran out and the game auto-selected dragons again. Who switched the selection is NOT known
(user asked; a person tapped the phone in a11/a13). Open problems, reported, NOT fixed:

1. Spare spells still exist when the partial/4th AD is already down (splash) — the 3+3+3+2 plan
   only removes them if the 4th AD is zapped.
2. Map taps go out without checking WHICH card is selected; `al.card_selected()` is unusable on
   battle frames (reads 4-6 cards). The raised white border is visible by eye (a14 recorder 41.1:
   dragon; 49.5: Lightning) — a detector would need measuring.

### a14 fixes (2026-09-17, user-approved "both" + AD midpoint request)

Pre-fix copies: `scratchpad/battles/a14_20260917/pre_fix/`. Red team on the a14 cast: Lightning was
selected at ~t23.4-25.0 by input the script never sent (CONFIRMED: every tap is journaled, no swipe
reaches the card bar); whether the script's dragon taps or that other input CAST the 2 bolts is
UNDECIDED (the dragon "refused" check cannot tell a cast from a red-zone refusal). No unexplained
camera move. The guard below covers both.

1. **Selected-card guard.** `hud.selected_card()`: the selected card has a thick white border; a
   near-white border-column pair 126-139 px apart scored >= 0.5 on 68 of 156 recorder frames (a9-a14)
   and 0.00 on the other 88. Graded by eye: dragon 38/38, Lightning 29/29, 1 false positive (a hero
   ability glow read as hero_b), missed only under a popup's dimming. Guard (`dragon_card_ready`):
   before every dragon or probe tap, if Lightning still has charges AND is read selected, re-tap the
   dragon card once; still Lightning → stop. Only a positive Lightning read blocks, so a hero glow or
   a missed dragon border cannot freeze deploying.
2. **Spare bolts.** After all targets, the remaining plan budget goes on the last zapped AD
   (`zaps.spend_spare`): all but the last in one chain, then a fresh `card_alive` check before the
   last (one screenshot per bolt cost ~2 s x 8 on a 1-AD base in the a9 replay).
3. **AD pairs at the midpoint** (user: "drop one in middle of both"). Wiki (pasted by the user):
   Lightning is ONE bolt, 2-tile radius (21 tiles), L9 560. A tile is ~25-33 px at battle zoom, so
   the radius is ~50-65 px; side-by-side ADs (a11/a14 lines 87.6-90 px apart) sit ~44 px from their
   midpoint. `strategy.PAIR_PX = 100`: closest pairs first, each AD in one target, aim at the
   midpoint; after the bolts each member is checked and one still standing is topped up at its OWN
   centre. UNVERIFIED LIVE that both take full damage at 1.5 tiles.

- `zaps.py` (extracted, ~144 LOC) holds the zap loop; attack7.py 600 → 530 LOC.

Measured offline (`replay_a10.py`, new `--switch-at T` and `--lightning N`):

| scenario                                 | a14 code                                      | fixed                                           |
| ---------------------------------------- | --------------------------------------------- | ----------------------------------------------- |
| Lightning selected mid-deploy, 13 spells | **2 bolts off the ADs** (t65.7, 67.1)         | 0 off; `wrong_card` → dragon re-selected        |
| AD cluster (a11 line)                    | 4 single zaps 3/3/3/skip, **2 left castable** | 2 pair zaps 3+3, 4/4 down, 5 spare cast, 0 left |
| a10 (4 separated ADs)                    | 11 bolts, 0 left                              | 11 bolts, 0 left, 0 off                         |
| a9 non-green (old harness)               | —                                             | 3 bolts + 8 spare, 15 dragons, 4 abilities      |

Tests: `test_battle_clock.py` 25 + `test_spots.py` 57 = **82 passed**; `pytest tests/ -q` 15 passed.
Mutations FAIL: a14 attack7 (cluster pairs/left-over, switch), a14 strategy (pairs), a blinded
`hud.selected_card` (4 graded positives).

**Live verification BLOCKED (2026-09-17):** capture portrait 1080x2392, foreground `com.whatsapp`.
Nothing tapped.

### a15 LIVE (2026-09-17, a14 fixes): VICTORY, 3 stars, 100% — +959,297 g / +608,166 e / +17,693 d (+260,000 g star bonus)

`battles/a15_20260917/`. Army panel full, CoC in front, battery 100%. Storage delta +1,215,097 g /
+868,166 e / +19,393 d. NON-GREEN (dark) scenery: edge views + ring probes ran live (6 and 7 probes).

- **Lightning x11 used = 11 journaled zap taps** (3 + 3 on the two ADs found, 5 spare on the last):
  nothing castable left, no off-AD cast. `wrong_card` never fired (no outside switch this battle).
- Only 2 ADs found (locate mid 1 / up 1 / down 0 / left 2 / right 1) — the known model weakness on
  non-green sceneries; both read destroyed after 3, so the 5 spare bolts hit rubble (the cost the
  user accepted). They were 236 px apart: the midpoint pairing did NOT run — still unverified live.
- Dragons 15/15: 30 dragon taps, 14 refused and never re-tapped; group 2 landed 6/7 and the review
  top-up found no accepted spot on screen, probed (2 probes) and landed the last one.
- DimGate live: two event popups dimmed the screen (review t65.7-68.7 and t89.9-93.5; the timer froze
  1:54 → 1:51 over ~7 s). No tap inside either window; the hero abilities waited until t69.8.
- Clock (recorder timer): all Lightning by ~2:47 left, group 1 ~2:23, support ~2:17, last dragon
  ~1:45. 13 pans, 0 relocalize.

## SUPERVISED BATTLE sup1 (2026-09-15) — no spells, each card once: VICTORY, +1,235,436 gold

User rules, now binding for attacks: **never select a spell card; never re-tap a
card (a second tap on the Log Launcher destroys it, a second hero tap fires the
ability — abilities OFF); do not spray the bar.** `match.py`'s 70 px comb breaks
all three and cast the spells in b224040 (+138,952 g) — do not run it again.

- Army: Dragon x15, Hog Rider x1, Log Launcher, 4 heroes, spells x0.
- Cards were labelled by eye from the prep frame. **`calibrate_bar` centres are
  wrong past the troop cards**: siege+hero cards sit on a wider pitch, measured
  drift 27-62 px (756 vs 729 ... 1510 vs 1448). Measured centres used:
  442, 586, 756, 916, 1056, 1196, 1345; grey spell at 1510.
- Result: Victory, >=1 star (damage % not captured — frame grabbed mid-animation).
  Gold 4,700,838 -> 5,936,274 (+1,235,436), elixir +957,228, dark 5,798 -> 13,311
  (+7,513). All deploys done by T+32 s. Scripts: session scratchpad
  `enter_scout.py`, `deploy_plan.py`.
- **Rule violation found in my own run:** `validated_site` re-taps the card on
  EVERY probe. All 6 probes (interior points) were refused, so the Dragon card was
  tapped 7 times, not 1, and ~30 s of clock went to probing. Replace probing with
  one card tap + first placement read from the grey/count change.
- prep countdown was already over at scout time (`prep_now=false` after 5 s).

## ACTIVE COMMAND + VERTICAL VIEW SCAN (2026-09-15, a1-a4)

User feedback, binding: **review the battle every 1-2 s until it ends and act at
once** (leftover troops, hero abilities); and **the landing view hides the top
and bottom of the base — pan to use them.** Scripts: session scratchpad
`attack1.py` (fire-and-wait, superseded), `attack2.py` (review loop),
`attack3.py` (+ prep-time vertical scan, batched drops). Card templates in
`scratchpad/cards/`, cut from sup1: right cards 0.905-1.000 on 4 fresh battles,
best wrong card 0.603.

| run | script  | gold delta | dark delta | notes                                                               |
| --- | ------- | ---------- | ---------- | ------------------------------------------------------------------- |
| a1  | attack1 | +484,319   | +2,416     | 82%, 2 stars; result showed only x10 dragons expended, no abilities |
| a2  | attack1 | +1,354,624 | +10,873    | user took over mid-battle                                           |
| a3  | attack2 | +1,669,748 | +11,372    | opening placed 1/15 dragons at x=0; rest at T+45 s; abilities T+45  |
| a4  | attack3 | +1,242,288 | +20,081    | view scan picked TOP; all dragons by T+25 s; abilities T+27         |

- **Pan, measured in prep:** one 380 px finger drag moved the camera -298.8 px
  (up) / +324.3 px (down), phase-corr response ~0.3. Largest safe-grass component:
  landing 67,190 px, top 217,934 (3.2x), bottom 141,591. Pan ONLY with no card
  selected (prep, before the first card tap) — a drag with a card selected may
  deploy.
- **Per-tap screencap confirmation is too slow for a whole wave** (~2 s/tap, a3
  needed 27 s for 11 dragons). Confirm until ONE lands, then batch the rest.
- Rule compliance a3/a4: spell taps 0; Log Launcher 1; heroes 2 each (land +
  ability once); dragon card selected 2-3 times, only while still coloured.
- **a5 FAILED: -1,400 g, 0 loot, 0 units placed; user ended it.** The view scan
  scored the top view 414,935 px, but the largest "grass" component was JUNGLE
  outside the map; `candidate_sites` added points inside the base. Every probe was
  refused, and the review loop re-probed the SAME points for 8 rounds (user saw
  rapid taps inside the base). Measured: jungle H41-44 S199-203 V69-109 vs real
  field H39-44 S157-205 V80-158 — **colour cannot separate them. Rejected.**
  A red-hue mask for the dashed deploy boundary was also tried and rejected: it
  lights buttons, fires, card art and wall trim, not the line (52-67k px of noise).
  Needed: never re-tap a refused point; candidates must come from ground adjacent
  to the base, not from the largest green blob.
- **Offline deploy-ground detectors for panned views — all REJECTED (a4/a5 frames):**
  - building-distance band (60-200 px from non-grass blobs >1500 px): trees count
    as "buildings", so the band follows the jungle; 9/12 a5 points in trees, a4
    nearest candidate 199.2 px from the accepted point.
  - texture (local V std, 31 px): jungle 19.0-39.9 vs accepted field 14.7 — a
    4.3 gap on ONE accepted point; rendered, the smooth mask marks the tile floor
    INSIDE the base and jungle clearings, not the deploy strip. The accepted a4
    point is not in it.
  - Saved frames are exhausted as ground truth: only one accepted point exists.
    Next evidence needs a live frame of the game's own red no-deploy shading in a
    PANNED view (does it cover the off-map jungle?).
- **Probe p1 (2026-09-15, user-approved, 0 units placed, ended via End Battle):**
  a refused Dragon tap on the base interior produced **NO red no-deploy shading**
  on the landing view or the top view — only Air Defense range rings on the top
  view. Badge delta 0.0 both taps (Dragon stayed x15). So "the game shades the
  no-deploy area red" cannot be triggered on demand this way; do not build on it.
  After a pan with the card selected, `card_selected()` read False although the
  card still looked highlighted in the frame — the raised-band test is likely
  confounded by the moved background; unproven either way.
- **Gotcha:** the village frame right after End Battle shows resource bars MID
  count-up animation (read gold 9,185,578 / gems 954 while the true values were
  11,174,598 / 1,113). Never read resources from the first post-battle frame.
- **a6 (attack4.py):** bottom view, 4 spots refused (never re-tapped), 5th
  accepted; +402,072 gold, +10,388 dark, gems 1,113. Rules held.
- **A real-money offer (Yeti Champion skin, Rs559) appeared on the village**
  between battles with no script tap; attack4 refused to start (`not_village`);
  dismissed via KEYCODE_BACK only, gems verified 1,113.
- **Rule update: Lightning allowed ONLY onto Air Defenses.** Lightning template
  cut from p1 prep (x=1480): self 1.000, best other card at that spot 0.428.
- **a7 (attack5.py): Defeat 43%, 0 stars, +966,128 gold.** Locator on the ONE
  chosen view: 11.3 s, 2 verified ADs (both correct by eye). 8 Lightning cast
  4+4, each confirmed by the badge; **3 Lightning unused** (no third target in
  view) and all 15 dragons in one bottom batch -> dragons died by T+111 s.
  User: scan the WHOLE map, zap every AD, split dragons across sides.
  The 15 "unknown" frames T+111-142 were the Defeat result screen, NOT the
  three-card pick (still never captured).
- Locator on panned p1 top view: 23.8 s, 3 boxes; 2 zoom-verified ADs, 1 at
  y 855 hidden behind the hero cards -> targets need centre y <= 840.
- **CORRECTION — the logged pan shifts were WRONG.** `phaseCorrelate` reported
  -298.8 (a4) / -304.7 (a5) px for a +380 px finger drag. Edge-patch matching on
  the same saved frames (patches from the edge the scene moves away from, full-frame
  search, HUD boxes excluded) gives **+496 / +501 px** for a +380 drag and
  **-473 / -476 px** for -380, 8/10 patches agreeing to the pixel, scores
  0.91-0.99. The scene glides ~1.27x the finger distance. Phase correlation is
  aliased by the tile/wall pattern — rejected. Centre patches fail because a
  ~500 px move pushes them under the card bar. Code: session `camera.py`.
  Horizontal drags still unmeasured.
- User asked for (a) a **strategy step** that plans spells/troops/heroes/abilities
  from the opening scan (`strategy.py`, pure function, offline self-check passes
  for 0-4 ADs) and (b) **frame recording every 4-5 s** for post-battle review
  (`recorder.py`, `screencap -p`, separate from the decision loop's grab path).
- **a8 (attack7.py) FAILED: -1,400 g, 0 units, 0 Lightning cast.** Pan 1 (up)
  measured OK: dy +498, agree 3/4. Pan 2 (back down) UNMEASURABLE: agree 0/5,
  scores 0.47/0.75/0.46/0.28/0.96 -> `cam_ok=False` -> fail-closed skipped the
  remaining 3 views, all 3 zaps and both dragon groups, and there was NO recovery
  path, so the battle timed out with nothing deployed. The planner itself worked:
  4 ADs from 2 views, plan zaps 4/4/3 (all 11), dragons 8+7. Recorder: 19 frames,
  0 failures. **Fail-closed must never mean "do nothing for 3 minutes":** a lost
  camera needs re-localisation against the saved view frames, then the landing
  view (4/4 historically) as the fallback.
- **a8 root cause + fix (offline, session `camera.py`):** the pan back from the
  top view moved the scene -495 px; a row-660 patch landed at y~115, outside the
  (130, 850) search window -> 0/5. The camera itself was fine: recorder frames
  matched the landing view at (0, 3) with 14/15 patches. Fixes: search window
  y 0-850 (HUD landings still rejected); rows 190/280 (drag down) and 700/790
  (drag up); 7 columns x 700-1700 between the loot panel and resource bars (the
  old x 500/1900 columns were HUD-discarded, leaving a4 mid->up 2/3 -> false
  unknown); `relocalize()` against the saved scan views on any failed pan.
  Offline gate, 7/7 PASS: a5 up +496 (9/10), a5 down -473 (6/6), a4 up +501
  (6/7), a4 down -476 (6/6), **a8 failed pan -494 (5/6)**, same-frame (0,0)
  (6/6), **relocalize a8 t0007.4 -> mid (0,3) (14/15)**.
- **Recorder cadence is NOT 4.5 s live:** a8 gaps 7.4-11.8 s (19 frames/193 s,
  0 failures) — `screencap -p` competes with the decision loop's grabs. Good
  enough for review, not for fine timing.
- **a9 NOT RUN — DEVICE BLOCKED (2026-09-16).** `attack7.py` (with relocalize +
  current-view fallback) returned `no_battle`; gold 12,561,740 / gems 1,113
  unchanged, so no search fee. Cause is the device, not the entry taps:
  `coc.cli status` -> **battery 13% discharging, screen OFF**, game pid 25014;
  raw `screencap -p` returns a 15,529-byte **portrait 1080x2392** (black) frame, so
  `grab_raw` yields None and `classify()` crashes in matchTemplate. Battery is
  below `MIN_BATTERY_PCT = 25`. Per the root contract this is `DeviceBlocked`:
  not retried, not worked around. The a9 camera fixes remain **unverified live**.
- Spells were retrained for a5 (x11 in the bar); template gating kept them untapped.
- User reports a mid-battle **three-card pick** (choose gold, else dark, else any).
  No frame of it exists yet — capture one before automating it.
- Open: pan mid-battle safely (needs a no-selection state or a proof that a
  selected-card drag does not deploy); damage % is still not read from the
  result screen.

## FIXES FOR BOTH m11 BUGS (2026-09-10) — offline green, LIVE VERIFICATION BLOCKED

Both root causes were red-teamed by fresh agents before any code was written.
Both SURVIVED; both of my stated MECHANISMS were wrong, and the corrections
changed the fix.

### BUG A — mechanism correction that mattered

I was going to tighten the badge crop. That would NOT have worked. Selecting a
card repaints its whole FACE, not just the border: on the m11 frames the digit
columns themselves moved **98.58** while the glyphs still read `x25`. The
control that settles it: on the frame pair where only card 442 was tapped, the
crop at card **1593 moved 50.53 with zero taps on it**, purely from LOSING
selection. A deploy counter cannot fire on a card you never touched.

So the fix is not geometry, it is comparing like with like:

- `Baseline` — a badge reading tagged with its card AND its selection state.
  `compare()` returns `landed=None` for `cross_selection`, `selection_lost`, or
  `baseline_unselected` instead of a number nobody should trust.
- `take_baseline()` selects the card ALONE and grabs, giving wave 1 a
  selection-stable zero. Costs ~1.4 s/card, ~7 s of a 180 s clock.
- `drain_card` now retires a card only on `landed is False`. Counting `None` as
  a miss is exactly how m11 retired four cards that were still full
  (`exhausted_ticks [0,1,2,8]` came entirely from the artifact).
- `card_selected()` — new. A selected card is RAISED, so mean V in the 30 px
  band above it separates **14 selected (158.8-177.2) from 140 unselected
  (91.6-142.7), gap +16.2**, and reads 130.1 = "none" on the calib frame.
  Absolute BORDER brightness was tried first and scored **0/14** — it just picks
  the brightest card art.
- `count_badge` clamped to x-45..x+66, inside the calibrated ±68.5 card box.
  Measured glyph extent is right-aligned and ends by x+55. The old x-10..x+95
  ran 26 px past this card's border and 20 px into the next one.

### BUG B — mechanism correction that mattered

Wrong on three counts. The anchor was NOT `loot_point` (the model's marker
overwrites it: `anchor = pts[ord(mk)-65]`, 11 of 14 waves ran on [860,270]); it
was not "dead centre"; and it was NOT "because the base is maxed" — the m11 base
has a 4,332 px open interior grass component. It is refused anyway because
everything inside the **red no-deploy line** is refused on ANY base.

The real regression: `loot_side` picked the legal component nearest the loot
with a flat 900 px floor. Interior courtyards clear that easily, and the ground
beside the storages IS interior. **Measured over 10 stored battle frames the
chosen component was NEVER the largest — 0.01-0.23 of its area.**
`match.deploy_points` (behind the recorded 99%-damage run) simply takes the
largest, and on the m11 frame returns points along the legal left-edge perimeter.

Two failed ideas, both killed by looking rather than by argument:

- convex hull of buildings → hull covers 52-63% of screen (players park builder
  huts at map corners), ring 0.1-5%. Useless.
- grass BRIGHTNESS as the no-deploy discriminator → Otsu splits cleanly
  (2.2-3.2 sigma) but splits by TERRAIN, not by the line: rendered, it marked a
  whole base interior "bright". Rejected.

What shipped instead — stop predicting deployability, ask the game:

- `loot_side` floor scaled to the largest component (`min_frac=0.35`) and picks
  the NEAREST POINT, not nearest centroid (a perimeter ring's centroid is
  meaningless). Returns `(anchor, loot, region)`.
- `waves.spread_pool(..., region=)` confines the pool to that one component.
- `candidate_sites()` — probes ONE point per component, `MIN_PROBE_SEP=220` px
  apart, ordered nearest-loot-first. m11's six probes were six cells of a single
  spot; they were never independent tests.
- `validated_site()` supersedes `validated_point` and its verdict is now
  **authoritative**. On total failure it falls back to the largest-component
  rule and records `point_unvalidated`, instead of deploying into refused ground.
- Re-aiming each cycle can no longer walk the anchor back out of the accepted
  region.

### Measured, offline (`scratchpad/aimeval.py`, 9 bases + m11)

| metric                               | OLD (m11)     | NEW                       |
| ------------------------------------ | ------------- | ------------------------- |
| chosen component is the largest      | **0/10**      | **7/10** (rest 0.38-0.69) |
| median clearance to nearest building | 28.7 px       | **45.1 px**               |
| pool points outside the aim region   | n/a           | **0**                     |
| first-6 probe x-span                 | ~0 (one spot) | 988-1819 px               |

### Gates

`scratchpad/test_fixes.py` — **15 checks, all pass**, every one replaying real
m11 frames so each would have failed before. Includes the direct regression:
card 1593 losing selection has raw `badge_delta` 50.53 and the `Baseline`
refuses it. `test_battlelog.py` 26/26 and `pytest tests/` 4/4 still green.

### STATUS: NOT verified live

The phone went unreachable before the verification battle: not advertising on
`_adb-tls-connect._tcp`/`_adb-tls-pairing._tcp`/`_adb._tcp` at all, and
`adb connect 192.168.1.4:38413` times out. **Nothing here is proven until a live
battle reads damage > 0%.** Offline proxies are proxies; m11 itself passed every
offline check it had.

## RUN m11 — first battle WITH per-action logging: 0% DAMAGE (2026-09-10)

`runs/20260910T142554Z_battle` — Defeat, **Overall Damage 0%**, gold_delta **-1,400**
(18,975,706 -> 18,974,306), zero loot. 66 taps / 17 groups / 52 map taps, 251.8 s.
Army was confirmed **300/300** before the match; shield was NOT broken by attacking
(1h52m -> 1h45m is natural countdown).

The logging paid for itself on its first run: both causes below were invisible in
every previous battle record.

### Step 0 PASSED — device timestamps are real

`date +%s.%N; input keyevent 0; date +%s.%N; sleep 0.20; input keyevent 0; date +%s.%N`
returned 3 parseable monotonic floats twice. `timing_source == "device"`, not estimated.
**Measured: one `input` command costs 46-82 ms of DEVICE time on its own** — so a real
inter-tap gap is the intended gap + ~60 ms. Run m11: intended 213.9 ms, measured 283.6 ms
(+69.7 ms), which matches. The estimated path would have hidden this.

### BUG A (confirmed) — `badge_delta` measures the SELECTION HIGHLIGHT, not units

`badge_delta` is large exactly when the selected card CHANGES and ~0 when the same card is
re-tapped. 14/14 groups, no exceptions:

| selected card_x          | vs previous | badge_delta                                    |
| ------------------------ | ----------- | ---------------------------------------------- |
| 586, 1593, 442, 730, 874 | CHANGED     | 63.23, 51.57, 76.94, 53.81, 52.88              |
| repeat of same card_x    | same        | 0.0, 0.0, 0.0, 0.01, 0.02, 0.05, 0.1, 0.0, 0.0 |

Direct visual proof: annotated frame `a007_deploy_tick0.webp` header says
`delta=76.94 landed=True`, while the card badge **in that same frame still reads x25**
(untouched) and the HUD reads `Overall Damage 0%`. So `landed` is a false positive on the
first wave of every card. This is the same failure mode as probe2 (crop included the card
border) — it is back, or was never fixed on this code path. Everything downstream
(`exhausted_ticks`, wave sizing, mop-up) is built on this signal.

### BUG B (confirmed) — every map tap targeted non-deployable ground

- Record says **`point_unvalidated: True`** — validation failed and the run proceeded anyway
  (the d1 "fall through unvalidated" fallback).
- `deploy_point [817,317]`, `loot_point [849,329]`, `side_anchor [821,343]` are all the SAME
  point, dead centre of the enemy base.
- `spread_pool()` ranks legal cells by distance to that anchor and keeps the nearest 40, so
  it aims **into** the base. Overlaying the mask on a real battle frame: all 40 picks land in
  x 630-1039, y 149-565 — on the building cluster.
- Zooming tap 0 of g07 in the annotated frame shows it landing **on top of a building**.
- The opponent was a wall-to-wall maxed base: `green_mask` = **25.3%** of screen vs **41.6%**
  on the earlier frame that did score damage. Almost no interior tile was deployable, so all
  52 map taps were refused.

Earlier matches paid 121,870-1,983,433 because those bases had wide open grass near the
anchor. Against a maxed base the same aiming rule yields zero.

### Secondary observations

- 42 of 52 map taps (81%) went into waves 2/3, which only re-tap an already-selected card.
  Wasted budget even independent of BUG B.
- **tick8 was a HERO card (level 49), not a troop.** The runner ran a 12-tap "drain card" on
  it. The model's `card_name` said "Dragon".
- Budget still binds at 58/58; peak/cell 2; 45 cells. The caps work — they were just
  spending taps on refused ground.

## PER-ACTION BATTLE LOGGING (2026-09-10)

Battles were a black box: only `tick, k, landed, grey, t, pts, gaps, secs` per
wave, which is why three rounds of "still spamming" had to be diagnosed by
re-deriving tap counts arithmetically. Now every tap is recorded with where it
went, what it was for, which card was selected, the gap since the previous tap,
and what changed after.

Stored through `coc.report.RunLog` in `runs/<stamp>_battle/`, so it obeys the
existing contract ("anything to analyse later must be a FIELD on the finish()
record"). `scratchpad/battlelog.py` + `test_battlelog.py`.

### Per-tap record

`i, group, group_kind, phase, kind, x, y, x0, y0` (post- AND pre-jitter),
`cell, cell_count_after, t_host, t_dev, dt_prev_ms, gap_intended_ms,
timing_source, card_tick, card_x, card_name, card_alive_before, card_sat,
intent, why, anchor, marker, dist_to_loot_px, budget_spent_after,
budget_remaining, spread_peak_after, batch_secs, batch_n`.

`card_sat` is the FLOAT, not the bool -- the margin is the diagnostic. `why` is
the model's own `reason`. `card_name` is recorded but **flagged unreliable**.

### Three things worth knowing

- **`RunLog.shot()` is PNG-only.** A full-res frame is ~2.4 MB; ~25 groups a
  battle would be ~60 MB per run and **>2 GB across the 40 retained runs**, on a
  disk already **90% full**. Annotations are written as half-res WebP instead:
  measured **129 KB each, ~3.1 MB a battle, ~124 MB for 40 runs** (q72 chosen
  over q80's 161 KB after measuring both).
- **`report._prune()` calls `f.unlink()` on every entry** in a run dir, so a
  subdirectory would raise. Annotation filenames are **FLAT**.
- **`RunLog.event()` is in-memory until `finish()`** and runs have died
  mid-battle (d1). Actions are also appended to `actions.jsonl` as they happen,
  which makes them crash-safe and `tail -f`-able for free.

### Measured per-tap delay -- best effort, degrades safely

Taps go out in one adb call with device-side `sleep`, so the host knows only the
INTENDED gap. `paced()` now interleaves `date +%s.%N` after each tap and parses
stdout: real device timing at **zero extra round-trips**.

It is stderr-silenced and the chain ends with `; true`, because **`dev.shell()`
RAISES on a non-zero exit** -- a device without a usable `date` must not make a
batch of taps that actually landed look like a failure. Unparseable output falls
back to `timing_source="estimated"`, recorded **per tap** rather than as a global
footnote. **Still unverified on the phone** (it was unreachable); the live check
is `date +%s.%N; input keyevent 0; date +%s.%N` -- `keyevent 0` is
KEYCODE_UNKNOWN, same `app_process` cost as a tap, zero game effect.

### Verified offline -- 26 checks, no phone (`test_battlelog.py`)

A `FakeDev` returns synthetic `date` output and records commands; the real
deploy path replays against a stored frame. Asserts, among others:

- every tap carries all required fields and a non-empty `intent`;
- **every deploy tap follows a `card_select` in the SAME batch** -- the
  invariant that stops a stale selection absorbing a map tap;
- **map taps == `budget.spent`**, and the log's per-cell tally matches
  `Spread.used` with none over the cap of 2;
- a device without `date` degrades to `estimated` and never raises;
- images defer during the battle and flush FLAT as WebP afterwards;
- `render_battle()` re-renders a HISTORICAL record offline.

### Reading it

`python3 battlelog.py <stamp|last|file.json>` renders a timeline offline:

```
      t kind         card                 taps  gaps(s)          outcome
    0.1 deploy       tick0 Baby Dragon       4  0.14 0.25 0.13   landed d=31.2 sat 132->118 dmg 7%
                     -> drain card tick 0, wave 1   (storages are here)
```

**Still open:** the live checks -- device timestamps, and confirming a real
battle dir stays under 5 MB with the record reaching `runs/runs.jsonl`.

## Where this session's code lives

Saved under `scratchpad/` **because the previous scratchpad was lost** — TODO
still references `scratchpad/enter.py`, `batch.py` and `deploy_area.py` that no
longer exist. None of this has been through the `coc/` contracts or the
verification gate; landing it is a separate task (see **## Next**).

| file                                                | what it is                                                                                                            |
| --------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| `scratchpad/autoloop2.py`                           | the battle loop: prep gate, bar calibration, grey-card test, wave deploys, spells, gated mop-up                       |
| `scratchpad/waves.py`                               | `Budget` (hard 58-tap cap), `Spread` (2 taps per 45 px cell), `spread_pool`, device-paced tapping, `paced() -> Batch` |
| `scratchpad/battlelog.py`                           | per-action logging: `TapCtx`, `BattleLog`, WebP annotator, `render_battle`                                            |
| `scratchpad/test_battlelog.py`                      | 26 offline checks with a `FakeDev` — needs no phone                                                                   |
| `scratchpad/match.py`                               | green-grass deploy detection, `loot_point`, BACK-only `to_village`                                                    |
| `scratchpad/batch.py`                               | run matches to a gold target; STOP flag + battery floor                                                               |
| `scratchpad/probe2-4.py`                            | the selection-persistence probes (probe4 is the one that settled it)                                                  |
| `scratchpad/vlmbench*.py`                           | the 24-model benchmark and its follow-ups                                                                             |
| `scratchpad/barfit.py`, `cardstate.py`              | FAILED card-segmentation attempts, kept so they are not retried                                                       |
| `scratchpad/zoomtest.py`, `diag.py`                 | pan/zoom capability probe; live calibration diagnostics                                                               |
| `scratchpad/mt/com/coc/Pinch.java` + `mt/pinch.dex` | the 2-pointer touch injector (zoom)                                                                                   |
| `scratchpad/runs/*.json`                            | every run record quoted in this file                                                                                  |
| `scratchpad/runs/matches.jsonl`                     | the 10-match farming session                                                                                          |

Rebuild the dex (JDK 25 refuses `-bootclasspath` with `--release`, so use
`-classpath`):

```bash
SDK=/opt/homebrew/share/android-commandlinetools
javac --release 17 -nowarn -classpath $SDK/platforms/android-36/android.jar \
      -d classes mt/com/coc/Pinch.java
$SDK/build-tools/36.0.0/d8 --min-api 34 --lib $SDK/platforms/android-36/android.jar \
      --output . classes/com/coc/Pinch.class && mv classes.dex mt/pinch.dex
```

Run one battle:

```bash
cd scratchpad && PYTHONPATH=.. python3 autoloop2.py <tag>
```

## HOME VILLAGE FARMING SESSION 2026-09-10 — 10 matches, +10,716,752 gold

Goal was 20,000,000 gold. **Reached 21,342,205** in 10 Casual matches, ~46 min
wall clock. Gold 10,625,453 -> 21,342,205, elixir 3,177,909 -> 12,599,288,
dark 285,070 -> 356,616. Total fees 14,000 gold (1,400 x 10). Gems 836 before
and after. Army: 25 Baby Dragons L8 + 4 heroes + 9 Lightning + 2 Freeze.

| #   | gold delta     | running total  | notes                                                   |
| --- | -------------- | -------------- | ------------------------------------------------------- |
| m1  | +821,411       | 11,446,864     | 48% dmg; ~2 min of clock wasted on manual inspection    |
| m2  | **+1,888,911** | 13,335,775     | ended T+42s; best single match recorded in this project |
| 3   | +1,075,790     | 14,411,565     | ended T+96.5s                                           |
| 4   | +1,068,235     | 15,479,800     |                                                         |
| 5   | +1,983,433     | 17,463,233     |                                                         |
| 6   | +1,024,623     | 18,487,856     |                                                         |
| 7   | +264,816       | 18,752,672     |                                                         |
| 8   | +679,947       | 19,432,619     |                                                         |
| 9   | +121,870       | 19,554,489     |                                                         |
| 10  | +1,787,716     | **21,342,205** | target passed                                           |

Mean **+1,071,675/match**, range 121,870-1,983,433 — the same base-to-base
variance the Builder Base runs showed. 150-215 s per match end to end.

### GREEN-GRASS COMPLEMENT SOLVES THE DEPLOY-POINT PROBLEM

This is the finding that mattered, and it retires "deployment strategy is the
open problem, not the plumbing".

**Clash shades the ENTIRE no-deploy area red at battle start.** So the
deployable region is not something to be inferred from a dashed line — it is
literally the visible green, and its complement is free. Recipe:

1. `inRange(HSV, (16,45,45), (52,235,245))` -> grass;
2. blank the HUD boxes; **erode by 26 px** so a point sits clear of the edge;
3. take the LARGEST connected component only — that enforces the
   concentrate-on-one-side doctrine geometrically rather than by choosing angles;
4. sample points along that component's long axis.

**10 of 10 matches found valid ground; not one hit the fallback.** Compare the
2026-09-09 red-boundary detector, which took 5 of 13 points (38%) on a maxed
player base. Tracing the boundary was never necessary — the game had already
filled it in.

### Card centres are NOT constants — the bar is CENTRED

`battle.CARD_X` is wrong for this army and is unsafe as a constant: the troop
bar centres itself on x~1196, so an 11-card bar and a 12-card bar put every
card at a different x (a 12th card appeared mid-battle in m1). Pitch measured
~145 px, cards ~120 px wide.

**Fix that needs no detector: tap a 70 px comb over x in [400, 2000]** at
y=975. Every card is hit whatever the count, and a tap in the gap between cards
is an inert no-op. Brightness-based card segmentation was tried first and
REJECTED — greyed-out dead cards and dark card art gave 5, 14 and 15 "cards"
on three frames of the same battle.

### SAFETY: the blind-tap exit walked into two money screens in one match

`fight.py`'s exit loop tapped `RETURN_HOME` / `OKAY_BUTTON` on a fixed schedule
until the village classified. In m1 that sequence went through:

- the **real-money Cosmetics shop** (Rs559.00 skins, a 1,500-gem item), and
- **"Upgrade Archer Tower to Level 21? — Confirm 4,000,000 gold"**.

Nothing was spent (gems 836 and gold 11,446,864 identical either side), but
this is the second time blind timed taps have reached a real-money screen —
see the 2026-09-09 Season Pass incident. **Blind taps on the village are now
forbidden outright.**

Replacement: `to_village()` uses **KEYCODE_BACK only** — it dismisses a result
screen, a shop panel and a building dialog alike and cannot spend anything. A
tap is a late fallback and only on a green button found inside the TIGHT box
**(1090,878)-(1320,962)**, which is Return Home / Okay and nothing else.
Validated to return None on all four hazards: the Cosmetics shop, the 4M
Confirm dialog, a clean village, and a live battle. Note a wider box DOES find
the 4M Confirm button and the shop's green resource bar at y~971-1049.

### Entry and the first wave must be in ONE script

m1 was entered by `enter.py` and fought by `fight.py`, and the ~2 minutes I
spent reading the frame in between came straight out of the 3-minute battle
clock: "All forces deployed / No spells left" by T+59s, battle still ended on
the timer at 48%. m2 merged the two and paid **2.3x** the gold on the same
doctrine. The clock is the scarce resource — never put a human between entry
and the first wave.

### Hypothesis raised and DISPROVEN in-session

Matches 7-9 fell to +264,816 / +679,947 / +121,870 as gold neared 20M, which
looked exactly like storages filling and clipping the intake. **Wrong.** Match
10 paid +1,787,716 and carried the total past 20M to 21,342,205, so the cap is
above 21.3M and those three were simply low-loot bases. Recorded because the
monotone-looking run was convincing and still meant nothing at n=3 against
sd this large.

### Re-confirmed

- **Attacking does not break the shield**: 7h15m -> 6h33m across 10 attacks in
  ~46 min — natural tick only.
- The army restores instantly and free between matches; no training wait was
  ever observed across 10 consecutive matches.
- `Next` was never used (its coordinate is still unverified and cost a fee for
  nothing once). Every base found was attacked.

**Scripts:** `match.py` (one full match), `batch.py` (loop to a gold target,
with a STOP flag and the `MIN_BATTERY_PCT` floor checked between matches).
Saved in `scratchpad/` — see **## Where this session's code lives**.

## VLM DECISION LOOP + PAN/ZOOM (2026-09-10)

Prompted by the observation that the blind runner **spams**: measured **1,167 taps
per match for ~46 deployable units (25.4 taps per unit)**, including 48 spell-point
taps for 11 spells and 24 hero-ability taps for 4 heroes.

### Model benchmark — 21 vision models, two tasks, hand-labelled truth

Truth read by hand off 4-5 stored frames (clock, "Overall Damage", `xN` badge).
Frames, prompts and scorer: `vlmbench.py` / `vlmbench3.py`.

| model                                                                 | p50       | time | dmg | dragons | pick  | empty-bar | $/1k  |
| --------------------------------------------------------------------- | --------- | ---- | --- | ------- | ----- | --------- | ----- |
| **google/gemini-2.5-flash**                                           | **3.3 s** | 4/4  | 4/4 | 4/4     | 4/4   | PASS      | 1.08  |
| openai/gpt-4.1-mini                                                   | 4.3 s     | 4/4  | 4/4 | 4/4     | 4/4   | PASS      | 0.90  |
| google/gemini-3-flash-preview                                         | 4.4 s     | 4/4  | 4/4 | 4/4     | 4/4   | PASS      | 1.01  |
| google/gemini-2.5-flash-lite                                          | 7.3 s     | 3/4  | 4/4 | 4/4     | 4/4   | PASS      | 0.29  |
| gpt-5.4-nano / gpt-4.1-nano / gemma-3-27b / nova-lite / mistral-small | —         | poor | 4/4 | mixed   | mixed | **FAIL**  | cheap |
| z-ai/glm-4.5v                                                         | 53.7 s    | 4/4  | 4/4 | 4/4     | 4/4   | PASS      | 3.81  |

`empty-bar` is a TRAP frame where every card is spent; a FAIL means the model
invents deploys there, which is the spam behaviour itself.

**Rejected outright:** `bytedance/ui-tars-1.5-7b` (multilingual garbage),
`qwen3.7-flash` (provider 429s), `gpt-5-nano`/`gpt-5-mini` (reasoning consumes
the whole token budget, empty content), `glm-4.5v` and `deepseek-v4-flash-vision-exp`
(19-54 s -- unusable inside a 3-minute battle).
**DeepSeek is mostly TEXT-ONLY** -- only 3 of 19 ids accept images, and
`deepseek-v4.1-flash` is blocked by _this account's_ OpenRouter data policy
("Paid model training violation"), not by capability.

### THE FINDING: models read the HUD but CANNOT AIM

Asked for raw deploy coordinates, the best model put **3 of 30** points on legal
ground. Graded rather than binary: **median miss 29 px, p90 191 px** — and a
29 px miss is a refused deploy.

Asked instead to **pick among CV-proposed numbered markers**, the same models
scored **4/4 valid** in 3.5-4.2 s, and on the empty-bar frame correctly chose
NOTHING.

**So: CV owns geometry, the model owns semantics and timing.** Do not spend
another hour trying to make a VLM output pixel coordinates.

### Capture is 2.8x faster than what the runner used

| method                                                     | median     |
| ---------------------------------------------------------- | ---------- |
| `exec-out screencap -p` (PNG, what `battle.grab_raw` uses) | 3.96 s     |
| `exec-out screencap` (raw RGBA)                            | 2.65 s     |
| **`shell screencap` + `adb pull` (raw)**                   | **1.43 s** |

That is what makes a ~6 s decide-act cycle possible at all.

### Aggregate bar saturation works where per-card segmentation does not

Per-card CV is NOT shippable: card slabs found in only 46/62 in-battle frames,
and the troops/siege/heroes/spells split correct in 18/62 (29%). Prep frames are
worse -- adjacent colour cards merge. But the AGGREGATE bar saturation tracks
troops remaining at **r=0.841**, monotone in-battle (53.8 -> 25.5 -> 23.2 -> 15.1
for 21 -> 13 -> 3 -> 0 dragons). n=5, so it is used as a relative change signal
and a second opinion, never as a count.

### PAN and ZOOM

- **Pan works** (`input swipe`; scene translates, measured scale 1.000).
- **`sendevent` to the touchscreen is DENIED by SELinux** even though shell is in
  the `input` group and can READ `/dev/input/event3`. Same class of block as
  `screenrecord`.
- Two CONCURRENT `input swipe` calls do **not** pinch -- measured scale 1.000,
  the camera merely translated twice. `input mouse` SCROLL does nothing
  (mean|diff| 2.5). Do not retry either.
- **SOLVED with a 3.6 KB dex**: `mt/com/coc/Pinch.java` builds a 2-pointer
  MotionEvent and injects it through `InputManagerGlobal` (Android 14+ moved
  `getInstance()` there), run as
  `CLASSPATH=/data/local/tmp/pinch.dex app_process / com.coc.Pinch ...`.
  Verified live: the village visibly zoomed out, whole base plus grass margins.
  Build: `javac --release 17 -classpath android.jar` (NOT `-bootclasspath`,
  which JDK 25 refuses with `--release`), then `d8 --min-api 34`.

### Live run a1 -- ABANDONED A BATTLE, Defeat 0%, 1,400 g burned

The model was called during the prep countdown, reported `troops_left: 48`, and
STILL set `done: true` ("Waiting for battle to start"). The loop trusted `done`
alone and left. Result screen: **Defeat, 0% damage, 0 loot, no troops expended.**

Fixes, both landed:

1. `done` now needs THREE agreeing signals -- the model's own `troops_left == 0`,
   `bar_saturation < 20`, and at least 2 calls made.
2. **An insurance sweep is unconditional**: before leaving, if the battle is live
   and the bar still has colour, fire the old blind sweep anyway. The
   state-driven path is an optimisation ON TOP OF a guaranteed fallback, never a
   replacement. The loop also refuses to return while `in_battle()` is true --
   in a1 that left `to_village` burning its whole 180 s budget inside a battle.

### Live run a2 -- works end to end

**+638,025 gold, 8 calls, $0.0084, clean exit, `left_in_battle: false`.**
Damage 3 -> 12 -> 33 -> 43 -> 49 -> 58%. Taps **730 vs 1,167 = 37% fewer**, and
now conditional: one round fired ONLY a hero ability for **3 taps**, and two
rounds correctly chose zero targets. Spells dropped once, not 48 times.

**Not yet good enough, and not to be oversold:**

- `troops_left` FROZE at 9 for seven consecutive calls while damage went 3->58%.
  Mid-battle counting is unreliable; the benchmark score was optimistic because
  those frames were the ones hand-labelled.
- `phase` flapped -- reported "prep" twice at 43% damage.
- **Loot is NOT yet comparable**: 638,025 against the blind runner's mean of
  1,071,675 is n=1 against a range of 121,870-1,983,433. Needs ~16 runs per arm.

### The account was RAIDED while this work was going on

Gold 21,342,205 -> 9,396,369 (-11.9M), elixir 12,599,288 -> 8,755,569, dark
356,616 -> 233,975, and the shield went UP (6h33m -> 6h44m), which is what
happens when you are attacked. **A 20M gold balance does not hold.** If the goal
is to SPEND 20M, farm and spend in the same session.

## PROBE + TROOP-SPAM FIXES (2026-09-10, later)

User reported the loop was STILL spamming troops. Root-caused, probed, fixed.

### Root cause: the decision schema had no card identity

`autoloop.PROMPT` returned `targets: [{marker, troops}]` -- no field naming a
CARD. So `execute()` could not target one troop type and looped over EVERY card
position, selecting each and dumping `n` units from it. `troops` was applied
PER CARD, not as a total. Every recorded tap count reconstructs exactly:

| moment     | formula                   | recorded |
| ---------- | ------------------------- | -------- |
| t=7.5 prep | 23 comb x (1+8) + 6 spell | 213      |
| t=21.2     | 9 cards x (1+8)           | 81       |
| t=46.3     | 8 cards x (1+8)           | 72       |
| t=68.1     | 9 cards x (1+8) + hero    | 84       |
| insurance  | 23 comb x (1+4)           | 115      |

**~637 map taps against an army of ~46 units (13.8x).**

### PROBE: "spent cards funnel their map taps into the last live card" -- REFUTED

A red-team pass proposed that a spent card leaves the selection intact, so its
map taps drain the previous card. Measured directly instead of argued, by
reading the COUNT DIGITS:

| trial                                  | before | after   | deployed |
| -------------------------------------- | ------ | ------- | -------- |
| baseline (select LIVE card, 1 map tap) | x24    | **x23** | yes      |
| baseline                               | x23    | **x22** | yes      |
| critical (tap SPENT card, 1 map tap)   | x22    | x22     | **no**   |
| critical                               | x22    | x22     | **no**   |
| critical                               | x22    | x22     | **no**   |

**Tapping a spent card CLEARS the selection.** `coc/flows/CLAUDE.md:104` is
correct as written; there is no funnel, and a slot sweep cannot over-drain one
card. It is merely INDISCRIMINATE -- it deploys every card type that has units.

_Method note worth keeping:_ probe2 got AMBIGUOUS because its badge crop
included the card border, which carries the SELECTION HIGHLIGHT -- tapping the
dragon card scored +73.5 and tapping the witch -72.1 from highlight alone, with
no deploy involved. Compare frames with the SAME selection state, and crop the
digits only.

### THE BIG ONE: DEPLOYS DO NOT REGISTER DURING PREP

Found while the probe kept failing. **`battle.in_battle()` cannot tell the
"Battle starts in" countdown from a running battle** -- it keys on a red button,
and prep shows "End Battle" where a live battle shows "Surrender", both red in
the same ROI. probe2 selected a card and issued 6 map taps across 10 s of prep
with ZERO effect; the countdown ran 14s -> 4s untouched.

**Every match this project has run fired its largest first wave into that
window.** This is the likely real source of the "~75% first-wave refusals" and
the "7.6 s queue lag" recorded on 2026-09-08.

Discriminator, measured: the Boost Army / Boost Heroes VIOLET buttons exist only
during prep -- **37.8-38.9% violet in prep vs 0.13-4.98% once running** (n=63
battle frames, median 1.57). `autoloop2.prep_active()`.

### Deploy points from the grass mask are NOT trusted until the game accepts one

probe4's first candidate was refused and its second accepted -- trees and
obstacles pass the grass filter. `validated_point()` now test-deploys one unit
and requires the count badge to move.

### Card segmentation: FOUR CV attempts failed, use numbered ticks instead

| approach               | result                                                  |
| ---------------------- | ------------------------------------------------------- |
| brightness runs        | 5, 14, 15 "cards" on three frames of one battle         |
| grass-complement       | 11 cards on 46/62 in-battle frames, **0/9 prep frames** |
| periodic grid fit      | **0/10** (ratio scoring biases to small n)              |
| level-badge dark blobs | pitch median swung 29-358 px                            |

Cause: the profile separates cards only once they GREY OUT and the gaps darken.
It fails on a full-colour bar -- i.e. exactly when the army is full.

**What works:** draw NUMBERED TICKS over the bar and let the model say which
tick sits on a named card -- **4/4 correct**. The same model is unreliable at
ENUMERATING (n_cards came back 10, 11, 12, 23) and misreads counts on spent
cards (it read the LEVEL badge "8" as a count). So: ask it to IDENTIFY, never
to enumerate, and let the GAME decide what is exhausted.

### Result: 1,167 -> 195 taps (83% fewer), and now precise

| runner                   | taps/match |
| ------------------------ | ---------- |
| blind sweep (`match.py`) | 1,167      |
| autoloop v1              | 730        |
| **autoloop2**            | **195**    |

Each decision is now exactly `1 card select + N map taps` (13 taps). Exhausted
ticks are detected by the count badge failing to move twice, fed back into the
prompt, and the model then switches card -- observed live switching to the
Lightning Spell at t=95.1 after tick 0 was marked exhausted.

Live runs: c1 **+528,181 g**, c2 **+1,337,181 g**, both clean exits, ~$0.008
of model spend each.

**NOT yet fixed / not to be oversold:**

- Ticks 0 and 1 both sit on the SAME card, so exhausting tick 0 does not
  exhaust tick 1; ticks should map to cards by ~144 px proximity.
- The `_landed` badge check gives false negatives (several False while damage
  climbed).
- **Loot is still not comparable.** +528k and +1,337k against the blind
  runner's mean of 1,071,675 over a 121,870-1,983,433 range is n=2. Needs ~16
  runs per arm.

## TICK -> CARD MAPPING FIXED (2026-09-10, later still)

The 70 px comb put TWO ticks on every ~144 px card, so measuring tick 0 empty
left tick 1 pointing at the same spent card. Run c2 spent 7 of 8 calls on the
Baby Dragon card for that reason.

### Calibration: the selection highlight outlines a card's BORDERS

Selecting a card brightens its BORDER, not its face. Diffing the bar rows across
one card tap gives NARROW spikes at that card's two edges -- measured x 371-374
and 510-519 at strengths 163 and 153, against a **no-tap noise floor of
col.max 8.3**. The midpoint of the pair is that card's centre.

Three dead ends, all measured, none to be retried:

| attempt                            | pitch found | result                                                              |
| ---------------------------------- | ----------- | ------------------------------------------------------------------- |
| median of adjacent peak gaps       | 130.2       | wrong; one bad gap drags the median                                 |
| lattice fit over accumulated peaks | 140.8       | drifts to **31 px** error by card 11                                |
| strongest peak pair anywhere       | --          | anchored on the PREVIOUSLY selected card, every centre 39-41 px out |

**What works:** PITCH is a GAME CONSTANT, not a per-battle unknown --
`(1882-443)/10 = 143.9` from hand-measured centres. Fit only the PHASE, from
the peak pair that BRACKETS the tapped x (the tap moves the highlight, so
spikes appear at both the old and the new card; bracketing picks the new one).

Live result: edges [373.5, 510.5] -> anchor 442.0 -> centres
`[442, 586, 730, 874, 1018, 1162, 1305, 1449, 1593, 1737, 1881, 2025]`,
**max error 3 px** against hand-measured truth. Ticks are now 1:1 with cards.

Calibrate during PREP: selection works there even though deploys do not, and a
live battle animates the battlefield behind the translucent bar (col.max 163
with no contiguous run).

### Effect

| run                | distinct cards used    | deploys landed | taps    |
| ------------------ | ---------------------- | -------------- | ------- |
| c2 (70 px comb)    | **1** (Baby Dragon x7) | 3/8            | 195     |
| **c4 (1:1 ticks)** | **6**                  | **8/8**        | **129** |

c4 used Dragon, Lightning Spell, Archer Queen, Barbarian King, Electro Dragon
and wall breaker across 8 calls, damage 0 -> 24%, cost $0.0084, clean exit.
**129 taps vs the blind sweep's 1,167 = 89% fewer.** The insurance sweep also
shrank (48 taps, one per CARD, vs 92 for the 70 px comb).

### Still wrong

- The model's `count` is unreliable -- it reported 49 for a Barbarian King,
  which is the hero LEVEL, not a count. Harmless only because the code clamps
  to 12 and the deploy is verified by badge delta.
- Card NAMES are shaky ("Electro Dragon", "wall breaker" for this army).
- **Loot still not comparable at n=1**: c4 paid +310,714, c2 +1,337,181,
  c1 +528,181, against the blind runner's mean 1,071,675 over a
  121,870-1,983,433 range.
- `validated_point` needed its candidate budget raised 5 -> 8: run c3 aborted
  with `no_accepted_point` after 5, while a diagnostic showed 4 of 6 candidates
  accepted. Trees and obstacles pass the grass filter.

## WAVE DEPLOYMENT + THE GREY-CARD TEST (2026-09-10)

User: "still spamming" (twice), then the decisive observation: **"when a troop is
completely deployed that card will become gray/blackish - but the script still
tries to tap it (witch)."**

### The measurement that was wrong

Tap counts had fallen 1,167 -> 129, but taps are not the thing to count. Run c4
commanded **~107 unit-deploys against an army of ~46 units (2.3x)**. Sources:
N units stacked on ONE pixel; the model's `count` (it reported **49** for a hero
-- the hero LEVEL); all 9 Lightning dumped at once onto a marker that was OPEN
GRASS; an unconditional 36-tap insurance sweep; and an ability tap appended AFTER
the map taps, so a batch ended with a card still SELECTED.

### THE GREY-CARD TEST -- the best detector in this project

A fully deployed card renders GREYSCALE. Mean saturation of the card art over
**55 hand-labelled card states**:

|       | min      | max      | median |
| ----- | -------- | -------- | ------ |
| alive | **63.1** | 151.4    | 132.4  |
| spent | 0.0      | **42.5** | 13.4   |

A clean gap with no overlap -> threshold **52.0**, and `card_alive()` scores
**55/55**. probe4 had already watched the witch go 96.7 -> 0.0 the instant its
single unit was spent.

This is checked BEFORE tapping. The badge-delta path needed two failed waves to
notice a card was empty, which is exactly why it kept tapping the witch. Grey
cards are also hidden from the model's overlay entirely -- it cannot pick what it
cannot see. (Telling it "EXHAUSTED_TICKS: 0" in text did NOT work: run d2 spent
4 of its 8 calls re-picking an exhausted tick.)

### Budget: one choke point, not per-site gating

Per-site gating had already been tried twice and failed. `waves.Budget` caps MAP
taps for the whole battle at `ceil(1.25 * 46) = 58`; every map tap must pass
`take()`. Over-deployment is now structurally impossible rather than discouraged.

### Other changes

- **Waves, not bursts.** `wave_line()` returns k spread points and ROTATES between
  waves. PCA alone collapsed to a single point on a narrow component in d4 (8 taps
  in one 45 px cell), so it now prefers `deploy_points()`' own spread (measured
  26-85 px apart) with a rotating window.
- **`count` deleted from the schema.** The model returns only `card_tick` +
  `marker`; wave size is a fixed ladder (2,5,5,5) and the STOP signal is the grey
  test / badge delta.
- **Selection-leak fixed structurally:** the select tap and its map taps always go
  out in the SAME paced batch, so a stale selection cannot absorb a map tap.
- **Spells** go to `loot_point()` and are REFUSED unless `green_mask == 0` (proves
  inside the base), max 2 per battle.
- **Pacing:** device-side `sleep` between injects inside one adb call (verified:
  4 x 0.25 s = 1.95 s incl. adb overhead), gaps randomised 0.12-0.30 s. Costs no
  host round-trips, so it does not burn the battle clock.
- **Mop-up** replaced the unconditional sweep: gated on budget + >25 s left, skips
  grey and exhausted ticks, stops after two barren cards.

### Results

| run             | units   | x army   | max taps/45px cell | gap stdev         | cards used | mop | spells    | gold     |
| --------------- | ------- | -------- | ------------------ | ----------------- | ---------- | --- | --------- | -------- |
| **c4 (before)** | **107** | **2.33** | --                 | 0 (uniform 45 ms) | 1          | 36  | 9 at once | +310,714 |
| d2              | **50**  | **1.09** | 3                  | 0.063             | 3          | 18  | 0         | +100,543 |
| d3              | 58      | 1.26     | 7                  | 0.055             | 2          | 0   | 0         | +51,363  |
| d4              | 58      | 1.26     | 8                  | 0.075             | 5          | 3   | 0         | +43,510  |
| **d5**          | 58      | 1.26     | 5                  | 0.057             | 4          | 3   | **2**     | +425,835 |

Live proof the grey test works: d4 skipped tick 8 with ZERO taps (`greyskip`), and
d5 had **2 drains stop the moment the card greyed**.

### STACKING FIXED PROPERLY -- it was arithmetic, not tuning

Two heuristic attempts (PCA line, then a rotating window over `deploy_points`)
moved peak stacking 8 -> 5 and no further. The cause was never the heuristic:

| source of deploy candidates             | distinct 45 px cells offered |
| --------------------------------------- | ---------------------------- |
| `deploy_points()` (what the waves used) | **9-13**                     |
| the legal grass mask itself             | **161-410**                  |

A 58-tap budget spread over 13 cells stacks **>= 4.5 deep by pigeonhole**, so no
rotation scheme could ever have worked.

**Fix:** `waves.spread_pool()` builds the candidate pool from the legal mask --
one representative point per 45 px cell, keeping the **40 nearest the anchor** so
concentration doctrine still holds (measured extent 366-517 px, ~10-13 tiles =
one attack frontage; a four-side thin ring measured 40% damage against 99%).
`waves.Spread` then caps taps at **2 per cell**, jittering BEFORE marking so the
cap applies to the pixel actually tapped. 40 cells x 2 = 80 capacity against a
58-tap budget.

| run         | peak taps / 45 px cell | distinct cells used |
| ----------- | ---------------------- | ------------------- |
| c4 (before) | 12+                    | --                  |
| d2          | 3                      | 19                  |
| d3          | 7                      | 26                  |
| d4          | 8                      | 16                  |
| d5          | 5                      | 25                  |
| **e1**      | **2** (the cap)        | **43**              |

e1 live: 58 units, 15 waves, 4 cards, peak 2/cell over 45 cells, mop-up 0,
clean exit, gems 862, **+613,974 gold**, $0.0053.

### WE WERE ATTACKING THE WRONG SIDE -- 6/6 frames

User asked why everything lands on one side. Two separate answers.

**One side is correct.** A four-side thin ring measured **40% damage** against
**99%** for one or two adjacent sides; thinly spread troops die piecemeal. Do not
"fix" this by spreading wider.

**But WHICH side was never chosen.** `match.deploy_points` samples only the
LARGEST green component (`lab == order[0]`), so the side attacked was whichever
patch happened to be biggest. Measured over 6 stored battle frames:

| frame      | chosen patch -> storages | best available side | sides to choose from |
| ---------- | ------------------------ | ------------------- | -------------------- |
| probe_diag | 878 px                   | **9 px**            | 8                    |
| p2_00      | 1025 px                  | 159 px              | 17                   |
| b010618_r0 | 896 px                   | 280 px              | 12                   |
| b011152_r1 | 826 px                   | 539 px              | 9                    |
| b010618_r2 | 743 px                   | 287 px              | 17                   |
| m1_r4      | 875 px                   | 146 px              | 15                   |

**Wrong side 6 out of 6.** This matters because the 99% run in the record came
from "hugging the boundary next to the storages", and storage-targeted attacks
measured ~2x the gold of edge-spraying (+485,628 vs +279,164).

**Fix:** `autoloop2.loot_side()` picks the green patch nearest `loot_point()`
(the gold/elixir storage centroid) instead of the biggest, and anchors on the
point of that patch CLOSEST to the storages. Re-aimed every decision cycle as
the base is destroyed. Offline the deploy point moved a mean **466 px closer**
to the storages (old nearest tap 341-798 px, new anchor 24-440 px); live in e3
the anchor sat 303 px from the loot.

| run | units | peak/cell | cells | anchor->loot | gold     |
| --- | ----- | --------- | ----- | ------------ | -------- |
| e1  | 58    | 2         | 43    | (pre-fix)    | +613,974 |
| e2  | 58    | 2         | 49    | (pre-fix)    | +525,254 |
| e3  | 58    | 2         | 51    | **303 px**   | +275,035 |

**The gold column proves nothing yet** -- n=1 per run against a
121,870-1,983,433 range. The loot-side fix is justified geometrically (466 px)
and by the existing storage-targeting measurement, NOT by these three numbers.

### Still open -- do not oversell this

- **The Budget cap is binding every run** (58/58 in d3/d4/d5). The loop still
  _wants_ to over-deploy; the cap is doing the work, which is the right safety net
  but means the decision layer is not yet frugal on its own.
- **Loot remains uncomparable**: +43,510 / +51,363 / +100,543 / +425,835 at n=1
  each, against the blind runner's mean 1,071,675 over a 121,870-1,983,433 range.
  Nothing here shows more gold -- only that the army is no longer dumped.
- `validated_point` capping at 3 candidates ABORTED a whole battle in d1
  (`no_accepted_point`, -1,400 g, no loot). It now falls through unvalidated
  instead of aborting; the per-wave badge check discovers legality anyway.

## State of knowledge — Builder Base (2026-09-09)

Authoritative summary. Detailed run-by-run notes are further down; where they
disagree with this section, this section wins.

### Established (verified against the live game)

| Fact                                                                      | Evidence                                                                             |
| ------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| **Gold is tiered strictly by STARS** — 3*=116,000, 2*=76,000, 1*=30,000   | counter delta checked every run; r9 (100%) and r10 (119%) both paid 116,000          |
| Builder Base attacks are **free**                                         | no fee on Start Attack, vs 1,400g in Home Village                                    |
| **Two-stage**: 3-starring stage 1 opens stage 2                           | r5, r9, r10, calib                                                                   |
| **Stage 2 grants the OTHER hero, fresh**                                  | hero card returns in colour as a Copter while stage-1 dragons are grey               |
| Army = 6 Baby Dragons L18 + ONE hero per stage                            | Start Attack screen                                                                  |
| **Battle Machine is GROUND** → deploy WITH dragons (cannot break Tantrum) | card art + wiki                                                                      |
| **Battle Copter is AIR** → space it >=190 px like a 7th dragon            | card art + Tantrum rule                                                              |
| Tile ≈ **38 px** at battle zoom                                           | wall-block spacing, p25-p75 23-42                                                    |
| Tantrum needs **>=4.5 tiles (~190 px)** from other AIR units              | wiki x2                                                                              |
| One spacing rule defeats FOUR mechanics                                   | Tantrum 4.5t, Air Bomb splash 1.5t, Mega Tesla chain 3.0t, Roaster splash 1.2t       |
| Dragons die by **T+37-54 regardless of spacing**                          | frame timelines r5/r6/r7                                                             |
| Up to **13 buildings can shoot air** at BH10                              | 3 Archer Towers + 5 Firecrackers + 3 Hidden Teslas + Air Bomb + Roaster + Mega Tesla |
| Card **saturation**: dead 0.0, alive 63-158                               | `card_alive()`, exact on ground-truth frames                                         |
| VLM result reading **4/4 exact**, ~3 s                                    | `vlm.read_battle_result()`                                                           |
| adb address is unstable; **serial is the only anchor**                    | 192.168.1.4:42131 -> 192.168.0.135:43801 mid-session                                 |

### Disproven or rejected — do not retry

- **"Separation orders outcomes."** FALSE: 193px->69%, 215px->100%, 257px->52%,
  279px->119%. `COMFORT_PX` is marked unsupported in the code.
- **"Each unit is immune to what kills the other."** Only true with the GROUND
  Battle Machine. With the Copter the army is ALL AIR and shares one threat set.
- **Arrow-badge "deployable" detector.** REJECTED after 3 attempts: the ⬇⬆ badge
  marks a NEWLY AVAILABLE card and fades — `live.png` had 6 deployable dragons
  and zero badges. Use "try every slot" instead.
- **`hero_ready()` alone.** Returned True on a result screen; must be gated on
  `in_bb_battle()`.
- **Red-boundary detection on maxed Home Village bases** (5/13). Works in the
  Builder Base only because the surround is plain green.
- **The shipped `loot_bubble` template.** Matches nothing at its own threshold,
  including on Home Village frames — bubbles scale with camera zoom.

### Open

- **Stage-2 O.T.T.O Outpost = a free extra star**, and gold is star-tiered, so
  this is the only known remaining upside. Never yet destroyed.
- Defence classifier: VLM localisation lands on real buildings but its LABELS
  are unverified (one "mega_tesla" looked like a Crusher). Validate against our
  own base, where tapping a building makes the game name it.
- Builder Base Cannon / Double Cannon per-BH counts — needed for the
  Hidden-Tesla counting trick.
- Damage across 11 runs: **mean 79%, sd 27, range 45-131**. Base difficulty
  dominates every deploy parameter tested.

### Process lessons (cost real value here)

- **Never `pkill` a runner mid-battle** — abandoned a live battle (0%/0 stars)
  and lost an unrecorded 90% run. Use the `STOP` flag.
- **Never diagnose a background run as dead from a stale log plus one frame** —
  did exactly that, double-deployed, and fired abilities early.
- **Every timed tap must be gated on a fresh screen check** — a timer-driven
  ability loop outran the battle end and walked into a real-money shop screen.
- **Verify identity by zooming, not glancing** — a low-res read of "Battle
  Machine" (actually a Battle Copter) sat under the doctrine for several runs.
- **n=1 is not a comparison** when sd is 27 points.

## Attack research (live, 2026-09-08/09)

Everything below is measured against the real device and the real game.
Helpers that survived are in `coc/battle.py`.

weekly attack allowance and a sign-up deadline, Casual is unlimited.
**Live end-to-end test 2026-09-08 — the pipeline works, the tactics did
not.** Sequence proven automatable: Attack -> army confirm -> Find a Match
-> battle -> batched deploy -> Return Home. 44 injects landed in 1.8s in
one `adb shell` call. Result: 22 dragons + 2 heroes deployed, **5% damage,
0 loot** -- everything dumped in one tight cluster on the left edge with no
spell support against a maxed base. Deployment strategy is the open
problem, not the plumbing.
**Costs were far lower than assumed** (all measured, not guessed):

- shield/guard **NOT broken** by attacking (4h50m -> 4h39m = natural tick)
- army **fully restored immediately** afterwards (4/4 heroes, 300/300,
  11/11, 3/3) -- no training time, no hero regen
- actual cost: **1400 gold search fee + trophies**, nothing else
  So attacks are cheap and repeatable; iterate on deployment freely.
  **Second attempt, perimeter spread — VICTORY, 80% damage.** Same plumbing,
  only the deployment changed, and that alone was the whole difference:
- attempt 1: all troops one tight clump, ONE side -> 5% dmg, 0 loot
- attempt 2: spread over THREE sides -> 80% dmg, **+1,365,417 gold /
  +1,288,590 elixir / +3,721 dark** for a 1,400 gold fee
  Star Bonus advanced 3/5 -> 4/5 (one more star unlocks 995k gold / 4,975 DE).
  **Working sequence, all coordinates verified live:**
  Attack (209,956) -> Find a Match (414,800, costs 1400g) ->
  army-confirm Attack! (1955,981) -> battle -> spread deploy ->
  mop-up pass -> Return Home (1196,929)
  **Deploy recipe that worked:** interleave points across the left strip
  (x=35, y 120-800), top strip (y=32, x 460-1940 skipping the countdown text
  at x1040-1410) and right strip (x=2355, y 380-680, below the resource bars
  and above the Next button). Then a mop-up pass cycling EVERY troop card
  against a few known-good points — empty cards no-op, so it needs no
  knowledge of what is left. 44 + 77 injects, 1.8s and 3.2s per batch.
  **Deploy geometry, mapped 2026-09-08 in a free sandbox.** The single-player
  level **Payback** (first level, already 3-starred so Available loot 0/0) is a
  zero-cost battle sandbox: resources were byte-identical before and after.
  Two structural findings:

1. **The red boundary is drawn PER BUILDING as an isometric diamond, not
   as one rectangle around the base.** Seen unambiguously on Payback,
   which has 2 buildings each with its own diamond. On a dense base the
   hundreds of diamonds merge into one solid central mass -- which is why
   the middle is entirely blocked and only a thin outer band is usable.
2. **All four EXTREME corners are deployable**, and so are the four
   mid-edges. Ground truth, not inference: 8 probe taps at (60,60),
   (2330,60), (60,850), (2330,850), (1200,50), (1200,855), (40,450),
   (2350,450) took the dragon card from x25 -> x17, i.e. 8/8 landed.
   Points underneath HUD overlays still deployed.
   **Detection status — what works and what does not:**

- tracing the red line FAILS on dense bases (0.1% of screen detected):
  buildings are drawn OVER the boundary, fragmenting it. Works on sparse
  maps (10.3% on Payback) via a hollow-outline test: boundary components
  fill <18% of their bbox, while dirt patches (49%) and the End Battle
  button (74%) are solid.
- grass-based detection is the better primitive, since the diamond is
  just the building footprint dilated by ~1 tile. **Grass is H 17-34
  (yellow-green), S 92-129, V 102-147** -- measured, and NOT the 28-95
  hue band initially assumed, which silently missed most of the field.
  **High-rate frame capture (2026-09-08) — and what it exposed.**
  `screenrecord` is BLOCKED on this device (ColorOS/SELinux): it returns
  "Permission denied" writing to /sdcard AND /data/local/tmp even though
  `touch` succeeds in both, so it is the capture capability, not the path.
  Working alternative -- capture RAW on-device, pull later:
  | mode | rate | size/frame |
  | screencap -p (PNG) | 0.61 fps | 4.7 MB |
  | screencap (raw RGBA) | 4.8-6.5 fps | 10.3 MB |
  `adb pull` runs at **12.26 MB/s**, so transfer is NOT the bottleneck.
  Recipe: device-side `while` loop writing /data/local/tmp/f$i.bin with a
  STOP flag file, run in background; afterwards pull a subsample and
  convert to WebP on the host (raw header is 12-16 bytes, then RGBA).
  295 frames in 45.6s = **154 ms/frame**, vs the ~12 s gaps of single
  screencaps -- an ~80x improvement in temporal resolution.
  **What that revealed, invisible at the old sampling rate:**
- deploy taps injected at t=13.4s; dragon card stayed x25 through
  t=19.8s and read x17 at t=21.0s; first troop spawn VFX visible at
  t=21.0s. **A ~7.6 s lag between injecting taps and the game acting.**
  The taps are QUEUED, not lost -- all 8 eventually deployed.
- during that window the scene is pixel-static (frame-to-frame change
  ~0.8 vs ~2.9-7.2 once live); even torch flames do not animate, i.e.
  the scene is rendered but the simulation has not started.
- **NOT caused by capture starvation** -- control on the home village:
  input->response latency 0.21 s at 4.8 fps capture and 0.0 s at 1.2 fps.
  **Actionable:** do NOT deploy immediately after the battle screen appears.
  Deploying 1.4 s after visual load gave the 7.6 s queue; deploying ~44 s
  after load (Triple A run) registered within one probe interval (~0.5 s).
  CORRECTION: the "wait until consecutive frames differ" rule I first
  proposed is WRONG and is not validated -- an idle live battle scene is
  also nearly static (consecutive-frame change 0.11-0.48 for 48 s while
  fully responsive), so frame-difference cannot distinguish "stalled" from
  "loaded but nothing happening". A settle delay is the working mitigation;
  the exact minimum is not yet measured.

**DENSE-BASE DEPLOY MAP (2026-09-08), ground truth.** Sandbox: single-player
**Triple A** -- 3-starred, Available loot 0/0, so free. 5x5 probe grid,
one dragon per point, 0.55 s apart, card-count delta = the reliable
success signal. **14 of 25 landed.**

    x=      60     640    1200    1760    2330

y= 60 Y Y N Y Y
y=260 Y Y N Y Y
y=460 Y N N N Y
y=660 Y N N N Y
y=850 Y N N N Y

- **Left edge x=60: 5/5. Right edge x=2330: 5/5.** Both fully reliable
  at every height -- these are the bankable deploy lanes.
- Top band (y=60, y=260) is open except dead centre.
- Everything else in the middle/bottom centre is inside the merged
  building diamonds and is refused.
  **RETRACTED 2026-09-09 — this does NOT generalise.** The same 25-point grid
  was run on three further free 3-starred campaign bases (Fort Knobs,
  Jump Around, plus Triple A above). The "left edge x=60 / right edge x=2330
  are bankable lanes" claim was overfitted to Triple A alone:

  how many of the 3 bases accept each cell (3 = unanimous)
  x=60 640 1200 1760 2330
  y= 60 1 3 1 2 2
  y= 260 2 3 1 1 2
  y= 460 2 0 1 1 3
  y= 660 3 0 1 0 3
  y= 850 3 1 1 2 2

Only 6 of 25 cells agree unanimously. x=60 ranges 1/3..3/3 and x=2330
ranges 2/3..3/3 -- neither is a reliable lane. Totals were similar
(14, 14, 13 of 25) but the PATTERNS differ completely: Fort Knobs
accepts the centre column x=1200 at three heights, where Triple A
refuses it at all five.
**Conclusion: deploy points CANNOT be fixed screen coordinates.** The
deployable region is the complement of the base footprint, and the camera
frames each base differently, so it must be detected per battle.
_Caveat on the method:_ probes run y-major over ~17 s, so later rows meet a
partially destroyed base and their successes are inflated. This does not
explain the disagreement, which is already present in row y=60 (probed in
the first ~3.5 s, before meaningful destruction).
**BOUNDARY DETECTOR BUILT AND VALIDATED (2026-09-09).** Three candidate
detectors were scored against the labelled deploy grids:

    detector                       score      per-base
    A  trace red boundary          64/75 85.3%   22/25, 21/25, 21/25
    B  grass + clearance           50/75 66.7%   18, 18, 14
    C  base footprint (closing)    51/75 68.0%   22, 17, 12
    baseline "assume all deployable"      59%

**A wins and is consistent across all three bases**, which matters more
than the headline number -- B and C are carried by one base each.
Method: Clash draws the red no-deploy boundary per building; mask red,
keep only THIN structures (subtract a morphological opening, so solid
red roofs/buttons drop out but the dashed line survives), close the
dashes into an outline, fill the largest contour's hull. Two dead ends
worth not repeating: a convex hull over ALL red pixels over-covers
badly (it hulls the roofs), and "deployable = grass" fails because the
base interior is full of grass between buildings.
Code: `scratchpad/deploy_area.py` -- `deployable_mask`, `is_deployable`,
`deploy_points`. NOT yet landed in `coc/`.
**TESTED ON A REAL MAXED PLAYER BASE 2026-09-09 -- IT FAILS.** Live
multiplayer match vs SHASHWATZEN. Of 13 detector-chosen deploy points,
**only 5 were accepted (38%)**, against 85% on campaign bases. The mask
predicted 61.7% of the screen deployable when the truth is a narrow
outer margin, and it drew a vertical band through the middle rather than
the base outline -- several chosen points sat squarely on buildings.
Cause: on a maxed base the red mask saturates with decorations, walls
and roofs, so the thin-structure filter cannot isolate the dashed
boundary. **Do not use `deploy_area.py` for multiplayer farming.** It is
campaign-only, and the campaign result does not transfer.
The same battle was then salvaged with the empirical perimeter lanes
(left x=35 / right x=2355 / top y=32): **Victory, 52%, +279,164 gold /
+358,270 elixir / +2,941 dark for a 1,400 gold fee** -- so the crude
empirical lanes still beat the detector on a real base.
**Star Bonus completed** by this win (4/5 -> 5/5): paid 995,000 gold /
995,000 elixir / 4,975 dark **into the Treasury** (not straight into
storages -- it needs collecting from there), plus ores to the Blacksmith.
**Limits, unvalidated beyond them:** tuned on CAMPAIGN bases only; on a
maxed player base the red mask is polluted by decorations and the hull
over-covers. The hull is convex so real concavities are lost -- it errs
toward "blocked", which is the safe direction. A refusal must still be
treated as normal and retried elsewhere.

**Label quality was the real bottleneck, not the detector.** The first
Fort Knobs grid scored 40% against detector A with BALANCED errors (5
false-Y, 7 false-N) -- the signature of noise, not bias. Cause: probes
0.70 s apart with an attribution window of [T+0.05, T+0.72], so adjacent
windows nearly touch and a slightly-late deploy is credited to the wrong
cell. Re-probing at 1.40 s spacing moved detector agreement 40% -> 84%,
while old-vs-new labels agreed only 48% with each other.
**Rule for any future probe run: spacing >= 1.4 s.**
Also measured: an Android notification banner covered native
(512,18)-(1880,70) during that run, contaminating 3 cells outright.
System overlays can intercept taps -- worth silencing before a run.

_Good news for detection:_ on these campaign bases the red dashed boundary
IS clearly visible and matches the ground truth exactly. The earlier
tracing failure was on a MAXED player base cluttered with red roofs and
decorations. Three labelled base frames + grids now exist as a validation
set for a boundary detector.
_Harness notes:_ navigation must be closed-loop -- the campaign map resets
to Goblin Capital, scroll is not repeatable (same 3 swipes put a node at
y=470 then y=441), so detect the orange level nodes and confirm the Attack
button before entering; three runs with hardcoded nodes silently entered no
battle and were only caught by an `in_battle` assertion. An Android
notification banner also appeared over the game mid-run -- system overlays
can intercept taps.
This is exactly why the earlier x=35 left strip worked in real battles.
**The game announces failures itself**: a red banner "YOU CANNOT DEPLOY
TROOPS ON THE RED AREA!" appears at y~135-170 (in 1196x540 space). Useful
as a signal that _a_ deploy failed, but it PERSISTS for seconds, so it
cannot attribute per-probe -- use the troop-card count delta for that.
**THE BATTLE CAMERA PANS — this invalidates every deploy map above.**
(2026-09-09) All prior grids were measured inside the ONE viewport the
camera happened to land on, and treated as if it were the whole world.
Swiping during a battle moves the camera freely. On a real match the sweep
showed the enemy base occupying only part of the map with a large open
grass field beside it -- so the "narrow outer margin" was an artifact of
framing, not a game rule. Fixed screen coordinates are meaningless without
first knowing where the camera is.
Sweep recipe that worked: `swipe_raw` 400<->2000 horizontally and
250<->900 vertically, ~1.5 s settle, with the raw capture loop running;
then pull the frame at each sweep timestamp and read the layout.
**Targeting loot beats spraying edges.** Having panned, the storages were
located from the frame (elixir ~(1550,550) and (1798,585), gold ~(1989,550)
in that camera position) and troops deployed on the grass adjacent to them:
**Victory 49%, +485,628 gold / +275,055 elixir / +2,554 dark for 1,400 g.**
Compare the previous real match, edge-spray only: 52% but +279,164 gold.
Nearly 2x the gold for the same fee.
Deploys are still being refused in bulk (20 of 25 dragons unused at the
40 s mark until a late dump adjacent to the base cleared them), so aim
point selection is still the weak link -- but the fix is camera-aware
targeting, not a static map.
**Best result so far, vs Brown Bear. :3 -- 99% damage, 2 stars, the FULL
available loot: +644,477 gold / +885,474 elixir / +7,544 dark for 1,400 g.**
Recipe, and it is the one to keep:

1. enter battle, capture a frame;
2. if the base fills the view, PAN to find its edge and the open field
   (`swipe_raw(700,300,1900,850)` revealed the upper-left corner here);
3. read the base boundary and storage positions off that frame;
4. deploy the army along a line HUGGING the boundary next to the
   storages -- not on screen-edge lanes, not on a static grid;
5. re-capture mid-battle and dump whatever is still in the troop bar
   adjacent to the surviving base.
   Step 5 matters: 19 of 25 dragons were still unused at 1m34s and the mop-up
   is what took it from 45% to 99%. Always re-check the troop bar.

**FARMING SESSION 2026-09-09: 9,985,736 -> 15,510,609 elixir in 7 battles**
(+5.5M, ~1,400 gold each). Per-match elixir gain and what drove it:
+1,408,132 one wall hugged + a second side (took full available+bonus)
+281,724 FOUR-SIDE thin ring -- only 40% damage, WORST result
+833,403 concentrated left+top corner + hard mop-up
+525,606 concentrated, low-loot base (took full available+bonus)
+647,968 panned to find edge, concentrated along boundary
+927,650 same, on a 1.49M-elixir base
+851,026 same
**Loot scales with destruction %, so CONCENTRATION beats spreading.**
A four-side thin ring got 40% damage; two adjacent sides with the whole
army got 99%. Thinly spread dragons are killed piecemeal before they
break through. Deploy along ONE or TWO adjacent sides, hugging the
boundary next to the storages.
**The mop-up is not optional.** Every single match had 18-20 of 25 dragons
still unused ~20 s after the first wave -- first-wave refusals run ~75%.
Re-capturing and re-firing 4 rounds against the base edge is what took
match 3 from 24%->40% and match 1 from 45%->99%. Always re-check the bar.
**Entry sequence needs a screen check.** The army-review screen does not
always appear; when it is skipped, the confirm tap at (1955,981) lands in
the battle TROOP BAR and burns spells. `scratchpad/enter.py` tests for the
red End Battle button before tapping confirm.
**Do not sleep during a live battle** -- the 3-minute clock is the scarce
resource. Search/Next phase is untimed and safe to wait in.
Also: `Next` at (2142,770) did NOT skip -- it exited to the village and
cost a 1,400 fee for nothing. Coordinate unverified; re-measure before use.

**Still open:** the deployable band on a DENSE base has no ground truth yet
-- calibrate by probing an already-3-starred dense single-player level,
which is free. Also unresolved: picking deploy points needs the base outline. Detecting the
red dashed boundary by HSV FAILED — the base is full of red decorations and
roofs, so the mask spanned the whole screen. Screen-edge strips worked as a
fallback but are camera-dependent; a real flow needs a better boundary
detector (try the grass/terrain texture outside the base, not the red line).
Builder Base 2.0 is two-stage with army carry-over.

## Builder Base (live, 2026-09-09)

Reached by tapping the **boat on the SW shore** of the Home Village. One tap,
no confirmation dialog. `assets/templates/boat_builder_base.png` was cut from a
live frame but is **NOT yet validated on a second pan** -- do not rely on it.

Code: `coc/builder_base.py`.

### It is a different screen space, not a re-skin

- **Three resource rows (gold, elixir, gems), not four** -- no dark elixir.
  Every row sits ~100 px higher than the Home Village equivalent.
- **SAFETY GAP:** the gem "+" buy button is at **(2003,240)-(2053,290)**.
  `safety.NO_TAP_ZONES` protects (1950,300,2392,430), which is BELOW it, so the
  Home Village interlock does **not** cover gem purchase here. See
  `builder_base.BB_NO_TAP_ZONES`.
- In battle, **Boost Army (353,715)-(649,788)** and Boost Heroes are gem spends
  sitting where the Home Village has nothing. See `BB_BATTLE_NO_TAP`.
- `KEYCODE_BACK` with no menu open raises **"Confirm Exit -- quit the game?"**.
  Cancel is at (985,690). Never send BACK blind here.
- Tapping a building both opens its menu **and moves the camera**, invalidating
  every other coordinate in the frame. Re-capture after each tap.

### Loot bubbles

The bubble sprite is **identical to the Home Village**; only the inner icon
differs. It is **not** fixed screen size -- it scales with camera zoom, so a
single-scale template match is unreliable. `builder_base.find_bubbles()` keys on
the olive frame colour plus frame/interior contrast instead, and is
zoom-tolerant. An open building menu scores -0.531 and is rejected.

The **Gem Mine produces a gem bubble** -- the only free gem income found so far.

### Attack runs (all free, Steel League II)

| Run    | Deploy | Abilities                      | Troops                                  | Damage   | Stars | Gold        |
| ------ | ------ | ------------------------------ | --------------------------------------- | -------- | ----- | ----------- |
| r1     | T+76s  | once, while engaged            | 6+BM                                    | 61%      | 2     | 77,000      |
| r2     | T+12s  | T+8 (before engaging)          | 6+BM                                    | 45%      | 1     | 30,000      |
| r3     | T+0.3s | T+40/75/110                    | **2**+BM                                | 59%      | 2     | 77,000      |
| r4     | T+0.6s | T+40/75/110 + stray early ones | 6+BM                                    | --       | 1     | 30,000      |
| r5     | T+0.7s | T+39/77/114 (too late)         | 6+BM, +2 stage 2                        | **131%** | 2     | **128,000** |
| r6     | T+0.6s | T+24/35 (loop lag)             | 6 spread +BM                            | 63%      | 2     | 76,000      |
| r7     | T+0.6s | **T+14/24 (on target)**        | 5 arc +Copter mid                       | **90%**  | 2     | 76,000      |
| r8     | T+0.6s | T+14/24                        | 6 @95px +Copter                         | 76%      | 2     | 76,000      |
| **r9** | T+0.5s | T+14/24                        | **5 @215px +1 reserve, BATTLE MACHINE** | **100%** | **3** | **116,000** |

- **Gold is tiered by STARS, not by damage percent.** 61% and 59% both paid
  exactly 77,000; both 1-star runs paid 30,000.
- **r3 reached 59% with only two Baby Dragons**, because a picker bug dropped
  four of them. The Battle Machine does most of the work.
- Ability timing is still **not** cleanly measured: every run so far varies the
  base as well, and r4 was polluted by stray early ability taps (below).

### Frame analysis of run r5 (900 frames @ 4.85 fps, whole battle)

Recorded with `RawCapture`, 25 frames pulled and read. Damage and surviving
troop cards over time (stage 1):

| T+s  | dragons alive | damage                   |
| ---- | ------------- | ------------------------ |
| 0    | 6             | 0%                       |
| 8    | 6             | 15%                      |
| 23   | 4             | 33%                      |
| 31   | 3             | 43%                      |
| 39   | **1**         | 58%                      |
| 54   | **0**         | 72%                      |
| 77   | 0             | 83%                      |
| 116  | 0             | 97%                      |
| ~120 | 0             | 100%, 3 stars -> stage 2 |

- **All six Baby Dragons are dead by T+54s**, at 72%. Everything from 72% to
  100% -- 28 points over ~65 s -- was the **Battle Machine alone**. Verified on
  the T+54 frame: all six cards greyscale, only the BM on the field.
- **The ability window is roughly T+10 to T+30**, while 4-6 dragons are still
  alive. The r5 schedule (T+39/77/114) was wrong: at T+39 only ONE dragon was
  left and at T+77/114 none, so two of three fires could only have helped the
  Battle Machine. This supersedes the earlier guess that "early is bad" -- the
  real rule is fire while the troops still exist.
- Dragons contribute the first ~70% quickly; the Battle Machine finishes. With
  a 3-star stage 1 this matters, because stage 1 must be finished to reach
  stage 2 at all.

### Builder Base 2.0 is TWO-STAGE -- do not stop at a fixed time

Three-starring stage 1 opens a **second base** with fresh troop cards, and the
result is the sum of both (r5 finished at **131% total damage**). Stage-2 cards
appear in the bar at x=1531 and x=1676 (the bar holds 8 slots, not 7).

The r5 runner assumed one stage and exited at T+185 while the battle was still
live; the user had to deploy the Battle Copter manually to finish it. A battle
loop must terminate on `in_bb_battle()` going false, **never** on a timer.

### Baby Dragon mechanics (researched online, 2026-09-09)

Two independent sources agree (Fandom wiki + Theria Games guide):

- **Tantrum** (passive): active only while the Baby Dragon is **>=4.5 tiles from
  other AIR units**; gives roughly **40-160% extra damage** plus attack speed.
  It switches OFF when another air unit closes inside that radius.
- **Fiery Sneeze** (active): **once per battle per dragon**, a cone of flame in
  front, and its damage is amplified while Tantrum is up.
- Counters: **Air Bombs, Firecrackers, Mega Tesla** -- Baby Dragons have low HP.
- **The Battle Machine is a GROUND unit, so it does NOT suppress Tantrum.**
  Pairing it with dragons as a tank is free.

**Tile size, MEASURED:** adjacent wall blocks (1 tile each) sit ~38 px apart at
battle zoom (p25-p75 23-42 px, the spread being isometric direction). So
**4.5 tiles is ~105-190 px**. Runs r1-r5 used deploy angles 10-15 deg apart on a
hull of ~400-600 px radius, i.e. **70-100 px between dragons -- below the
threshold, so Tantrum was suppressed the whole time.**

### r6: spread test (Tantrum-aware), 63% / 2 stars / 76,000

Deployed with min pairwise separation **309-565 px** instead of 70-100.

| T+s | alive | r6 damage (spread) |     | T+s  | alive | r5 damage (clustered) |
| --- | ----- | ------------------ | --- | ---- | ----- | --------------------- |
| 6   | 6     | **21%**            |     | 8    | 6     | 15%                   |
| 13  | 4     | 28%                |     | 23   | 4     | 33%                   |
| 16  | **2** | 35%                |     | 31   | 3     | 43%                   |
| 29  | 1     | 52%                |     | 39   | 1     | 58%                   |
| 39  | **0** | 59%                |     | 54   | **0** | 72%                   |
| 49  | 0     | 63% (final)        |     | ~120 | 0     | 100% -> stage 2       |

- **Spread dragons do more damage per second early** (21% by T+6 vs 15% by T+8)
  -- consistent with Tantrum being live.
- **But they die much faster**: 4 of 6 dead by T+16, all dead by T+39, versus
  T+54 clustered. Alone, each dragon eats a defence's full attention.
- **The decisive variable is not dragon damage, it is whether the BATTLE MACHINE
  SURVIVES.** In r5 it lived and carried 72% -> 100%, unlocking stage 2 and
  128,000 gold. In r6 it died with everything else at T+56 and the run stopped
  at 63% / 76,000. I deployed it ALONE on its own angle in r6; in r5 it shared a
  flank with the dragons and defences split their fire.
- **Confounded:** r5 and r6 are different bases. The mechanism is visible in the
  curves but the comparison is not controlled.

**Next experiment:** dragons spread >=210 px apart (keep Tantrum) but the Battle
Machine deployed INTO the dragon group rather than on its own flank -- legal
because BM is ground and does not break Tantrum.

**Defect found:** the r6 loop grabs a frame each iteration (~4-6 s) plus a 4 s
sleep, so ability taps landed at T+24 and T+35 instead of the intended T+14/24.
Timed taps must be scheduled off a clock, with the battle check done separately.

### r7: arc spread + Battle Machine mid-arc -- 90% / 2 stars / 76,000

Dragons spread on ONE flank at >=210 px (Tantrum kept on), Battle Machine
deployed in the MIDDLE of that arc rather than isolated. Abilities fired at
T+14.3 and T+24.3 (intended 14/24 -- the clock-scheduling fix works).

| T+s | dragons alive | damage          |
| --- | ------------- | --------------- |
| 12  | 5             | 18%             |
| 19  | 5             | **36%**         |
| 25  | 3             | 50%             |
| 37  | **0**         | 58%             |
| 68  | 0             | 72%             |
| 112 | 0             | **90%** (final) |

**The decisive variable is Battle Machine survival, confirmed across 3 runs:**

| run                 | dragons dead at | damage then | BM outcome        | final                    |
| ------------------- | --------------- | ----------- | ----------------- | ------------------------ |
| r5 clustered        | T+54            | 72%         | survived          | 100% -> stage 2, 128,000 |
| r6 360-deg scatter  | T+39            | 59%         | **died T+56**     | 63%, 76,000              |
| r7 arc + BM mid-arc | T+37            | 58%         | survived to T+118 | 90%, 76,000              |

- All three runs land at **58-72% when the last dragon dies**, regardless of
  spacing. The dragons front-load a roughly fixed share.
- The BM then adds **+28 (r5), +32 (r7), ~+4 (r6, died early)**. That difference
  is the whole spread between a 63% run and a 100% run.
- So spacing tuning matters far less than keeping the Battle Machine alive.
  Placing it mid-arc among the dragons (r7) beat isolating it (r6).

**Defect:** the arc planner fitted only **5 of 6** dragons at min_sep=210, and the
6th was never deployed (its card stays colour all battle -- that is the
persistent `a=1` in the timeline). Relax min_sep or place the leftover at the
arc end.

**Note:** still not controlled -- every run is a different base. The BM-survival
correlation now has 3 points but no run has repeated on the same base.

### adb address is not stable -- serial is the only anchor

Device reconnected mid-session and came back on a different subnet AND port:
`192.168.1.4:42131` -> `192.168.0.135:43801`. `Device.connect()` rediscovered it
by serial via dns-sd with no intervention. Confirms the standing rule.

### Builder Base defence knowledge base (wiki, 2026-09-09)

`assets/bb_defenses.json` -- all 16 defences + 4 traps, sourced one page at a
time. Nothing guessed: unconfirmed fields are null, and the Cannon carries an
explicit caveat that only the HOME VILLAGE page was captured.
API: `builder_base.load_defences() / threatens(unit) / free_targets(unit)`.

**The finding that matters: each of our units is immune to what kills the other.**

|                | dragons (air)                                                                                     | Battle Machine (ground)                                                                        |
| -------------- | ------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| killed by      | Archer Tower x3, Firecrackers x5, Hidden Tesla x3, Air Bomb, Roaster, Mega Tesla, X-Bow(air mode) | Crusher x2, Cannon, Double Cannon, Multi Mortar, Giant Cannon, Lava Launcher + the shared ones |
| kills for FREE | Cannon, Double Cannon, **Crusher**, Multi Mortar, Giant Cannon, Lava Launcher                     | **Firecrackers**, Air Bombs                                                                    |

- The **Crusher** is the BM's worst threat (highest damage per hit in the BB) and
  **dragons are immune to it**.
- **Firecrackers** are the dragons' worst threat (5 per base, 9 tiles) and the
  **BM is immune to them**.
- So the role split is: dragons clear Crushers, the BM clears Firecrackers.
  Runs r1-r7 sent both at whatever was geometrically nearest instead.

**Why dragons always die at T+37-54 regardless of spacing:** at BH10 up to 13
buildings can shoot air (3 Archer Towers + 5 Firecrackers + 3 Hidden Teslas +
Air Bomb + Roaster + Mega Tesla). No arrangement of 6 Baby Dragons survives
that. They are a TIMED RESOURCE delivering ~60%, not a force to be kept alive.

**One spacing rule defeats four mechanics** (all measured against ~38 px/tile):

| mechanic                     | radius            | our >=190 px spacing |
| ---------------------------- | ----------------- | -------------------- |
| Tantrum bonus (+40-160% dmg) | needs >=4.5 tiles | satisfied            |
| Air Bomb splash              | 1.5 tiles         | defeated             |
| Mega Tesla chain             | 3.0 tiles         | defeated             |
| Roaster splash               | 1.2 tiles         | defeated             |

**Abilities:** Fiery Sneeze is ONCE PER BATTLE per dragon, cone-shaped, and
amplified while Tantrum is up. Fire it in the measured T+10-30 window while
dragons are alive and engaged; clustered Firecrackers are the ideal target.

**Stage 2:** destroying **O.T.T.O's Outpost awards an EXTRA STAR regardless of
damage**, and we measured that gold is tiered by stars. Level 16+ Baby Dragons
can snipe it with Fiery Sneeze (3-4 needed); ours are level 18. In r5 we
reached stage 2 and spread out instead of sniping.

**Our army is unusually well matched to this base set:** Push Traps cannot touch
us at all (air immune + the BM explicitly cannot be pushed), walls are bypassed
by air and do not count toward destruction %, and the Lava Launcher is
near-harmless (dragons air-immune, BM resists its burn DoT).

### Perception limits -- what a classifier can NEVER see

- **Hidden Teslas (up to 3, hit BOTH air and ground) are invisible** until a unit
  comes within 6 tiles or 51% of the stage falls.
- **All 4 trap types are invisible too**, and Mines / Mega Mines can be SET to
  air -- unseen anti-air on top of the Teslas.
- Teslas CAN be inferred by counting: defences per stage are fixed by Builder
  Hall level, so quota minus identified-visible = hidden Teslas. This makes
  near-perfect RECALL the classifier's real target.
- Traps cannot be inferred at all -- they are not buildings and never appear in
  the quota.
- **NET: no computed "safe corridor" is provable.** Plans must degrade
  gracefully when a dragon dies to something that was never on screen.

**Open gaps:** Builder Base Cannon and Double Cannon per-BH counts are
unconfirmed, which is exactly what the Tesla-counting trick needs.

### r9: Battle Machine doctrine -- 100% / 3 STARS / 116,000 (best yet)

First run with the **Battle Machine** as hero instead of the Battle Copter, and
the first 3-star. The hero swap was the single change that mattered.

- **BM deployed WITH the dragon cluster** (pad 60 at the mid angle). Legal
  because it is GROUND: it cannot suppress Tantrum, and it pulls fire from the
  four both-targeting defences.
- **Separation preferred over headcount:** 5 dragons at **215 px** (>= the 190 px
  Tantrum threshold) instead of cramming 6 in at 95 px as r8 did.
- **6th dragon held in RESERVE** and deployed at T+28 once the first wave thinned
  -- exactly what the Baby Dragon guide recommends for keeping Tantrum active.
- Fiery Sneeze at T+14.2 / T+24.3.

| run    | hero                 | dragons           | sep        | damage   | stars | gold        |
| ------ | -------------------- | ----------------- | ---------- | -------- | ----- | ----------- |
| r7     | Copter (air)         | 5                 | 276 px     | 90%      | 2     | 76,000      |
| r8     | Copter (air)         | 6                 | 95 px      | 76%      | 2     | 76,000      |
| **r9** | **Machine (ground)** | **5 + 1 reserve** | **215 px** | **100%** | **3** | **116,000** |

Gold 1,545,678 -> 1,661,678 (+116,000, exact). Trophies +20.

**STAGE 2 WAS WASTED AGAIN -- and this time it was the expensive one.** A crash
in `plan_deploy(n=1)` (`min()` over an empty pair list) killed the stage-2
handler at T+28; the salvage loop only polled and tapped the BM card while
stage 2 ran. 3-starring stage 1 is precisely what unlocks stage 2, so the run
that most deserved a second stage got nothing from it. Compare r5, which reached
stage 2 and paid 128,000.

Fixed: `plan_deploy` now uses `min(..., default=inf)` -- a single unit is
trivially past any separation threshold.

**Stage 2 has now been mishandled in 3 of 3 attempts** (r5 assumed one stage and
exited on a timer; r8's handler was never reached; r9 crashed out of it). It is
the largest remaining source of lost value: the O.T.T.O Outpost awards an extra
star regardless of damage, and gold is tiered by stars.

### r10: stage 2 finally reached -- 119% / 3 stars / 116,000

The stage-2 handler ran for the first time in four attempts (every branch wrapped
so a bug logs and continues instead of aborting a live battle).

- Stage 1: same doctrine as r9 -- Battle Machine WITH the cluster, 3 dragons at
  279 px, 3 held in reserve and deployed at T+30 (sep 333 px).
- **STAGE 2 entered at T+86**, 2 troops deployed toward a detected O.T.T.O
  Outpost candidate at (1009,794). Final **119% total damage, 3 stars, 116,000
  gold, +22 trophies**.

**MISS: the free stage-2 hero was never deployed.** Builder Base 2.0 gives BOTH
heroes -- the selected one (Battle Machine) fights stage 1, and the OTHER one
(Battle Copter) appears FRESH in stage 2. The stage-2 code filtered cards to
`x > 1450`, which caught the two new dragons and never looked at the hero slot at
x~431. Frame evidence: at T+86 the hero card is back in COLOUR as a Copter while
dragons 1,2,3,5 are grey.

Fixed: `builder_base.hero_ready()` -- a dead/grey hero card measures ~1.9 mean
saturation, a live one ~93.0. Validated on 3 frames.

**Gold did NOT rise with the extra damage:** r9 (100%, 3 stars) and r10 (119%,
3 stars) both paid exactly 116,000. This re-confirms gold is tiered by STARS, not
damage -- so the remaining upside is the 4th star from destroying the O.T.T.O
Outpost, not more percentage.

| run | hero(s) used               | damage | stars | gold    |
| --- | -------------------------- | ------ | ----- | ------- |
| r9  | Machine (stage 1 only)     | 100%   | 3     | 116,000 |
| r10 | Machine; **Copter wasted** | 119%   | 3     | 116,000 |

### r11: 69% / 2 stars / 76,000 -- stage 2 never opened

Same doctrine as r9/r10 but separation was only **193 px**, barely over the
190 px Tantrum threshold. Stage 1 was not 3-starred, so stage 2 never opened and
**the new stage-2 hero code (`hero_ready`) went unexercised -- still unproven.**

Separation across the three Battle Machine runs (different bases each time, so
suggestive only):

| run | sep    | damage | stars |
| --- | ------ | ------ | ----- |
| r10 | 279 px | 119%   | 3     |
| r9  | 215 px | 100%   | 3     |
| r11 | 193 px | 69%    | 2     |

Hypothesis worth testing: comfortable separation beats scraping past the
threshold. `plan_deploy` currently ACCEPTS the first n whose sep >= 190; it
should probably prefer a smaller wave with much larger separation, holding more
dragons in reserve.

### r12 + STOP TUNING: parameter effects are below the noise floor

r12 used the new comfort-preferring planner: 4 dragons at **257 px** (vs r11's
193 px), 2 in reserve. Result **52% / 2 stars / 76,000** -- the WORST of the four
Battle Machine runs, with the second-best separation.

| run | sep    | damage   | stars |
| --- | ------ | -------- | ----- |
| r11 | 193 px | 69%      | 2     |
| r9  | 215 px | **100%** | **3** |
| r12 | 257 px | **52%**  | 2     |
| r10 | 279 px | **119%** | **3** |

**Separation does not order the outcomes.** Across all 11 runs damage is
mean 79%, sd 27, range 45-131. Base-to-base variance swamps every spacing and
timing parameter at one run per configuration -- exactly the sample-size problem
noted when ML was discussed (~16 runs per arm to resolve a 20-point effect, ~63
for 10 points). `COMFORT_PX` is marked UNSUPPORTED in the code.

**What IS established and repeatable:**

- **Gold is tiered strictly by stars:** 3* = 116,000, 2* = 76,000, 1* = 30,000.
  Verified against counter deltas every run. Extra damage inside a tier pays
  nothing (r9 100% and r10 119% both paid 116,000).
- **Both 3-star runs used the Battle Machine**; no Copter run ever 3-starred.
- Stage 2 requires 3-starring stage 1, and carries the unclaimed 4th star
  (O.T.T.O Outpost, awarded regardless of damage).

**Therefore: stop tuning deploy parameters.** The remaining upside is not
percentage, it is STARS -- specifically the Outpost star. That needs targeting
(hit the Outpost / Firecrackers deliberately), which is a mechanism change and
the actual justification for the defence classifier.

Also unresolved in r12: `Troops expended` showed x5 dragons though wave 4 +
reserve 2 = 6 were commanded, so one deploy tap did not land. Worth checking the
reserve card indices.

### Stage-2 deploy bugs found while batching (2026-09-09)

**1. Surviving dragons RETURN to the deployment bar.** Three-starring stage 1
sends survivors back to the bar in their ORIGINAL slots (x<1450). The stage-2
code filtered cards to `x>1450` -- the two new slots only -- so returned
survivors were never deployed. Observed live: 3 dragons plus the free hero left
unused. Fixed by attempting EVERY slot (0-8): a dead card no-ops, an on-field
card merely fires its ability, and the map tap is inert without a selection.

An arrow-badge detector was tried first and REJECTED: white-arrow pixels
separated cleanly on 3 frames (deployable 1356/184 vs on-field and dead 0) but
failed on a 4th. A detector right 3 times in 4 is not safe to route deploys on.

**2. `hero_ready()` is unsound alone.** It measures only card-region saturation
and returned True on a battle RESULT screen. Every caller must gate it behind
`in_bb_battle()` first.

**3. Never `pkill` a runner mid-battle.** It abandons a LIVE battle: one kill
produced a 0% / 0-star / 0-gold result screen, another lost an unrecorded 90%
run. `batch.py` now checks a `STOP` flag file between battles instead.

**4. A stale result screen blocks the village gate.** `ensure_bb_village` failed
4 attempts because the game sat on a leftover result screen. `dismiss_point()`
resolves it correctly (green Return Home at (1196,926)); the runner should clear
a result screen explicitly before asserting the village.

**Still open:** stage-2 deploys reportedly still not landing even after fix 1 --
under instrumentation (`calib.py`), one card at a time with a capture between
each, to separate "tap ignored" from "deploy refused". Note the stage-2 geometry
yielded only **8 of 24** valid deploy angles, so bad points are a live suspect.

### Safety incident, 2026-09-09 -- timed taps outrun the battle

A timed ability batch kept firing after the battle had already ended. The taps
landed on the result screen and navigated into the **Season Pass shop, which
carries a real-money offer (Rs559.00)**. Nothing was purchased (gems 994 before
and after) but the exposure was real. Contributing causes, all mine:

- Ability taps were sent on a fixed schedule with **no check that a battle was
  still on screen**. Fixed: `builder_base.in_bb_battle()` must gate every timed
  tap.
- I read a background run's log before it had written its deploy line, captured
  a frame 3 s before that deploy, concluded the script was dead, and deployed a
  second time. The cards were already spent, so those taps fired abilities early
  -- the very thing the run was testing against. **Never diagnose a background
  run as dead from a stale log plus one frame.**
- A `modal_present` check keyed on red pixels in the top-right reported a modal
  on clean frames: the Builder Base parks a red-and-white striped boat there.
  Fixed to key on the dialog panel's brown fill (0.695 vs 0.003-0.083).

### Attacking

- **Attacks are FREE.** No 1,400 gold fee, unlike the Home Village.
- Army is fixed per attack: Battle Machine (lvl 30) + 6 Baby Dragons (lvl 18).
- **The whole enemy base fits on one screen.** No camera panning -- which is the
  single biggest difference from Home Village attacks, where treating the
  landing viewport as the world invalidated every plan.
- **The red boundary detects cleanly here** (plain green surround) where it
  failed on maxed Home Village bases (5/13). `builder_base.base_hull()`.
- **There is a prep countdown ("Battle starts in: 54s") before the clock runs.**
  Use it to compute the plan, then deploy at T=0. On this run the prep window
  was spent on detection and the first troop landed with only 1m44s left.
- **Troop cards become ABILITY buttons once deployed.** Tapping cards 3-6 and
  the Battle Machine took damage **18% -> 54%** in one batch. Greyed card = that
  troop is dead. Firing abilities is free damage and was nearly half the result.
- Deploying by clamping points to `y_max` collapses several angles onto one
  line; pick angles that do not need clamping.

## Verified numbers (real device, real game)

| Measurement                          | Value                                       | How                                                      |
| ------------------------------------ | ------------------------------------------- | -------------------------------------------------------- |
| adb reconnect after `adb disconnect` | 12.2 s                                      | `Device.connect()` via dns-sd                            |
| `input` inject, one adb call each    | 79 ms                                       | 10x `input keyevent 0`                                   |
| `input` inject, batched in one call  | 44 ms                                       | 10 injects, single adb shell                             |
| `screencap -p` full frame            | 5.3–8.7 s                                   | 2.2 MB PNG over wifi                                     |
| scrcpy headless frames               | 10.2 fps                                    | 3 s recording decoded in OpenCV                          |
| Collect run, end to end              | 21–30 s                                     | `python3 -m coc.cli collect`                             |
| Village proof: digits parse          | 4/4 village, 0/4 every panel                | 22 village + 4 panel frames                              |
| `read_resources()` per frame         | 14.1 ms                                     | vs ~8 s to grab the frame                                |
| Recover from a stuck panel           | 16.3 s                                      | `ensure_village()`, one BACK                             |
| Battle deploy, 44 injects            | 1.8 s                                       | one batched `adb shell`                                  |
| Attack cost (Casual)                 | 1400 gold + trophies                        | shield & army unaffected                                 |
| Cluster-dump attack result           | 5% damage, 0 loot                           | 22 dragons + 2 heroes, 1 side                            |
| Perimeter-spread attack              | **80% damage, Victory**                     | same army, 3 sides                                       |
| Loot from one Victory                | +1,365,417 g / +1,288,590 e / +3,721 DE     | cost 1,400 g                                             |
| Storage-targeted attack              | +485,628 g / +275,055 e / +2,554 DE         | 49%, cost 1,400 g                                        |
| Edge-spray attack (same day)         | +279,164 g / +358,270 e / +2,941 DE         | 52%, cost 1,400 g                                        |
| **Pan-first, edge-hug attack**       | **+644,477 g / +885,474 e / +7,544 DE**     | **99%, 2 stars, cost 1,400 g**                           |
| Dense-base deploy probe              | 14/25 points valid                          | Triple A, 5x5 grid, free                                 |
| Reliable deploy lanes                | x=60 and x=2330, 5/5 each                   | every height                                             |
| Live collect #1                      | 6 taps, 0 bubbles left                      | gold +61,502 / elixir +64,946 / dark +722                |
| Live collect #2                      | 2 taps                                      | dark +33                                                 |
| Live collect #3 (via CLI)            | 1 tap                                       | dark +26                                                 |
| **Farming session, 10 matches**      | **+10,716,752 gold**                        | 10,625,453 -> 21,342,205, ~46 min                        |
| Gold per match, 10 matches           | mean +1,071,675, range 121,870-1,983,433    | `matches.jsonl`                                          |
| Match end to end                     | 150-215 s                                   | enter -> deploy -> mop up -> village                     |
| Green-grass deploy detector          | **10/10 matches found ground**              | vs 5/13 (38%) red-boundary detector                      |
| Shield across 10 attacks             | 7h15m -> 6h33m (natural tick)               | attacking does not break it                              |
| Gold storage cap                     | **> 21,342,205**                            | counter still rose past 20M                              |
| **Grey-card test** (`card_alive`)    | **55/55** labelled states                   | spent 0.0-42.5 vs alive 63.1-151.4, threshold 52         |
| Prep vs live battle (`prep_active`)  | violet 37.8-38.9% vs 0.13-4.98%             | `in_battle()` CANNOT tell them apart                     |
| **Deploys during prep**              | **do not register**                         | 6 map taps over 10 s of prep, zero effect                |
| Card-bar pitch                       | **143.9 px**, a game constant               | (1882-443)/10; fitting it per-battle drifts 31 px        |
| Bar calibration (selection borders)  | centres within **3 px**                     | 4 CV segmentation attempts failed first                  |
| Spent card clears selection          | baseline x24->x23->x22; spent x22 x3        | probe4; refutes the 'funnel' theory                      |
| Frame capture, raw + pull            | **1.43 s** vs 3.96 s exec-out PNG           | 2.8x faster                                              |
| VLM raw deploy coords                | **3/30** legal, median miss 29 px           | models read HUD but cannot aim                           |
| VLM picking labelled markers         | **4/4** valid                               | CV proposes, model chooses                               |
| Attack side chosen by area           | **wrong 6/6 frames**                        | 743-1025 px from loot vs 9-539 px best                   |
| `loot_side()` re-aim                 | **466 px closer** to storages (mean)        | 8-17 sides available each time                           |
| Units commanded per battle           | **107 -> 50-58** (2.33x -> 1.09-1.26x army) | hard-capped by `waves.Budget`                            |
| Peak taps per 45 px cell             | **12+ -> 2**                                | `waves.Spread`; pool was 9-13 cells vs 161-410 available |
| Model cost per battle                | **$0.004-0.008**                            | gemini-2.5-flash, 4-8 calls                              |

| BB attack cost | **0 gold** (free) | Start Attack dialog, no fee shown |
| BB attack result | 61%, 2 stars, **+77,000 gold** | 6 baby dragons + Battle Machine |
| BB gold before/after | 322,903 -> 399,903 | exactly +77,000, elixir unchanged |
| BB abilities, one batch | damage **18% -> 54%** | 4 dragon + 1 Battle Machine taps |
| BB bubble collect | gold +2,448 / elixir +2,475 / **gems +10** | 3 bubbles, 3->2->1->0 |
| BB trophies | 3441 -> 3417 (-24) | reward panel said +12; defence loss suspected |
| RawCapture cleanup | **5.8 GiB reclaimed** | 600 frames, `df /data` before/after |

## Gotchas worth remembering

- **Zone bounds are measured, never estimated.** Every entry in
  `safety.NO_TAP_ZONES` and `templates.HUD_ZONES` carries the element box it
  came from. Regression for any zone edit: re-run `find_loot_bubbles` over
  every frame in `runs/*/*.png` (22 frames, 34 bubbles) and require the
  result to be identical. A too-wide zone loses loot with no error.
- **World objects are camera-relative; HUD is not.** The boat sat at
  (895,555) only for one particular pan. Anything outside the HUD must be
  found by template match, never by a stored coordinate.
- **Panels are where the money is.** Events carries "one-time skin offer"
  promos behind green `Go!` buttons; My Army carries `Boost ARMY` /
  `Boost Heroes`. Both are gem spends, and both sit on screens that
  `classify()` currently mislabels or cannot name. Never tap inside a panel
  by coordinate; leave via KEYCODE_BACK, which worked on all four.
- **Star Bonus is league-scaled**, not fixed: at Witch 17 it is 995,000 gold
  / 4,975 dark (League Overview panel). It is earned by attacking, so there
  was no claim affordance on screen during the scout.
- **A transient PORTRAIT frame happens mid-transition.** Grabbing while the
  battle loads returns 1080x2392 and `_canonicalise()` raises CaptureError.
  The game had NOT left the foreground -- the next grab was fine.
  `ScreencapSource.grab()` has no retry, so a real attack flow needs one.
- **NO_TAP_ZONES are Home-Village coordinates applied globally.** In a
  battle the same rectangles cover the troop bar and End Battle, so the
  interlock blocks legitimate deploys while protecting nothing. Zones must
  become screen-scoped before any attack flow ships.
- **The game disconnects when idle** and shows "Anyone there? ... Reload game".
  Because runs are an hour apart this is the _normal_ first screen, not an edge
  case. `ensure_village()` handles it.
- Gold storage is near cap, so a successful collect can move the counter by 0.
  Progress is judged by bubbles disappearing, not by the resource delta.
- `uiautomator` works on the game (4 nodes) but returns only a bare
  `SurfaceView` — no usable structure. It fails entirely on the ColorOS
  launcher, which is a red herring, not a device-wide fault.
- A stuck `screenrecord` (pid 5722) from a capture probe is idle-blocked on the
  phone and unkillable under SELinux. Harmless; clears on reboot.
