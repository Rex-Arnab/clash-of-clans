# coc/flows/ — game behaviours

Inherits [`../CLAUDE.md`](../CLAUDE.md) and the root [`CLAUDE.md`](../../CLAUDE.md).

## Purpose

Sequences that actually play the game. A flow composes capture + vision + safety; it is the only
layer that knows game rules.

## Ownership

- `home_collect.py` — `collect_home()`: Home Village loot collection. The reference implementation
  for every flow that follows.

Planned (see `TODO.md`): Builder Base collect, free claimables (Star Bonus, Trader), attacks.
The working Home Village attack is not a flow yet: it lives in `scratchpad/` with its own contracts
([`scratchpad/CLAUDE.md`](../../scratchpad/CLAUDE.md)). Landing it here must keep every one of them.

## Local contracts

- **A flow decides _what_ to tap. It never decides _whether a tap is allowed_.** Tap only through
  `Tapper`; let `UnsafeTap` propagate into the result's `refused` list rather than catching it into
  silence.
- **Start every flow with `assert_manifest_matches()` → `wait_for_game()` → `ensure_village()`.**
  Never assume the village is already on screen.
- **Loop as detect → act → re-detect, bounded, with a no-progress break.** This is deliberate: it is
  correct whether or not tapping one collector sweeps all of that type (a wiki claim that could not
  be verified), it _measures_ that answer as a side effect, and it self-corrects a missed tap.
  `MAX_ROUNDS = 4`.
- **Progress means fewer bubbles, never a higher counter.** Storages are near cap; a successful gold
  collect can move gold by 0.
- **`dry_run` breaks after the first round.** Nothing was tapped, so the screen cannot change and
  further rounds would report the same bubbles forever.
- **Return a dataclass result; do not print and do not decide the exit code.** `cli.py` owns
  presentation. Log every decision through `log.event()` and both a `00_before` and `99_after` shot.
- **Read resources before _and_ after** so the run record carries a delta even when it is 0.

## Work guidance

- New flow = new module + a `@dataclass` result + one `cmd_*` in `cli.py`. Keep the flow signature
  `(device, log, dry_run=False)`.
- A flow that needs a new screen or template stops and gets the perception work done first — do not
  paper over a missing template with fixed coordinates.
- Attacks are **not** a collect flow with more taps: Home Village should farm **Casual** (unlimited),
  not Ranked (weekly allowance + sign-up deadline), and Builder Base 2.0 is two-stage with army
  carry-over. Read `TODO.md` before starting one.

## Attack contracts (hard-won; see TODO.md "Attack research")

- **The battle camera PANS. Never treat the landing viewport as the world.**
  Every deploy map built before this was measured inside one unmoved window and
  is worthless. Pan first (`swipe_raw`), find the base edge and the open field,
  then choose aim points relative to what you can actually see.
- **Deploy coordinates can never be constants.** The same screen point is
  deployable on one base and refused on the next -- measured across four bases,
  only 6 of 25 grid cells agreed. Read the base position per battle.
- **Concentrate, do not spread.** Loot scales with destruction %. A four-side
  thin ring got 40% damage; the whole army along one or two ADJACENT sides,
  hugging the boundary next to the storages, got 99%. Thinly spread troops die
  piecemeal before breaking through.
- **Always mop up.** First-wave refusals run ~75%: every observed match still
  had 18-20 of 25 dragons in the bar ~20 s in. Re-capture, re-fire several
  rounds at the CURRENT base edge. This step took matches from 24%->40% and
  45%->99%, and is worth more than any first-wave cleverness.
- **A refused deploy is normal, not an error.** The game says so itself with a
  red banner, but it persists for seconds and cannot attribute which tap
  failed -- confirm a deploy by the troop-card count changing
  (`battle.deploy_landed`), never by a success message.
- **Never `time.sleep` through a live battle.** The 3-minute clock is the
  scarce resource; the search/Next phase is untimed and safe to wait in.
- **Aim at buildings only through `coc.vision.locate.deploy_targets()`** — model-only, conf >=
  0.80 (owner's decision 2026-09-17). Never `locate_buildings()` defaults: those add a VLM verify
  that recovers more buildings but let 2 false ones through in 19 confirmations. A false Air Defense
  costs 3 Lightning; an Air Defense the model did not see is simply not a target.
- **When a troop card runs out, the game auto-selects the next card with charges.** A map tap past the
  last unit casts Lightning (a11). Deploy one unit per tap with a fresh card check, and never tap the
  map while Lightning is selected (a14) — see `scratchpad/CLAUDE.md`.
- **Pan one axis at a time.** A diagonal drag cannot be measured (all its patches lie under the HUD)
  and each fallback relocalize cost ~30 s of the 3-minute clock (a10).
- **Event popups pause the battle and take taps.** "Pick a Reward!" dims the screen for ~10 s while
  `in_battle()` stays True; tap nothing until it clears (a12-a15).
- **Check the screen before the army-confirm tap** (`battle.enter_multiplayer`).
  The army-review screen is not always shown, and the confirm coordinate lands
  in the troop bar when it is skipped, burning spells.
- **Assert `in_battle()` before trusting any in-battle measurement.** Three
  probe runs silently entered no battle and produced fabricated results.
- Costs, measured: **1,400 gold per search plus trophies. The shield is NOT
  broken and the army restores instantly and free**, so attacks are cheap and
  repeatable -- iterate on tactics freely.

## Builder Base contracts (see TODO.md "Builder Base")

- **The Builder Base is a different screen space, not a re-skin.** It has three
  resource rows, not four, so every HUD row sits ~100 px higher. The Home
  Village `safety.NO_TAP_ZONES` does **not** cover its gem-purchase button.
  Use `coc.builder_base.BB_NO_TAP_ZONES` / `BB_BATTLE_NO_TAP`.
- **Never send `KEYCODE_BACK` blind here** — with no menu open it raises
  "Confirm Exit — quit the game?". Classify the screen first.
- **Re-capture after every tap.** Tapping a building opens its menu _and_ moves
  the camera, invalidating every other coordinate in the frame.
- **Attacks are free** (no 1,400 gold fee) and the whole enemy base fits on one
  screen, so the camera-pan blind spot that ruins Home Village attacks does not
  apply. The red boundary detects cleanly on the plain green surround.
- **Deploy at T=0.** A prep countdown runs before the battle clock; compute the
  plan during it rather than after.
- **Fire troop abilities.** Once deployed, troop cards become ability buttons;
  one batch of taps moved damage 18% → 54%. Skipping them wastes about half the
  attack.

## Builder Base attack doctrine

Authoritative summary lives in `TODO.md` -> "State of knowledge — Builder Base".
Defence facts are in `assets/bb_defenses.json` (`builder_base.load_defences()`).

- **Deploy in STAGE 2 by trying EVERY card slot.** There is no reliable visual
  "deployable" flag — the ⬇⬆ badge means _newly available_ and fades. A dead
  card no-ops, an on-field card merely fires its ability, and the map tap is
  inert without a selection, so trying all slots is safe and complete.
- **Stage 2 grants the other hero, fresh.** Check for it; it is a whole extra
  unit and was wasted twice.
- **`hero_ready()` must be gated on `in_bb_battle()`** — alone it reports True
  on a result screen.
- **Do not tune deploy spacing on single runs.** Damage is mean 79%, sd 27 over
  11 runs; separation did NOT order outcomes. Roughly 16 runs per arm are needed
  to resolve even a 20-point effect.
- **Gold is tiered by STARS, not damage.** The only known remaining upside is the
  extra star for destroying the O.T.T.O Outpost in stage 2.

- **The army is ALL AIR: 6 Baby Dragons + 1 Battle COPTER** (verified from the
  troop-card art, 2026-09-09 — it is NOT a Battle Machine). So there is no
  ground unit, and no free counter to Firecrackers or Archer Towers; that
  damage must simply be absorbed.
- **The whole army is immune to every ground-only defence** — Cannon, Double
  Cannon, Crusher, Multi Mortar, Giant Cannon, Lava Launcher, Push/Spring
  Traps — and bypasses Walls. Never spend a plan on any of them.
- **One hero per attack: Copter XOR Machine — and the choice changes the plan.**
  The **Battle Copter is AIR**: space it >=190 px from dragons or it suppresses
  their Tantrum (7 air units to separate, not 6 — the r7 'hero mid-arc'
  placement was cancelling the bonus). The **Battle Machine is GROUND**: deploy
  it WITH the dragons, since it cannot break Tantrum and it pulls fire from the
  four both-targeting defences. Prefer the Machine.
- A ground hero still cannot shield dragons from **Firecrackers or Air Bombs** —
  those are air-only and ignore it completely.
- **Dragons are a timed resource, not a force to keep alive.** Up to 13 buildings
  can shoot air at BH10. They reliably deliver ~60% and die by T+37-54 in every
  run regardless of spacing. Plan around that, do not fight it.
- **Battle Machine survival is the win condition.** It added +28 and +32 points
  after all dragons died (r5, r7); where it died early the run stopped at 63%
  (r6). Everything else is secondary.
- **Space dragons >=190 px.** One rule satisfies the Tantrum bonus and defeats
  Air Bomb splash, Mega Tesla chain and Roaster splash simultaneously.
- **Fiery Sneeze is once per battle per dragon.** Fire it in the T+10-30 window,
  while dragons are alive and engaged; a Firecracker cluster is the best target.
- **In stage 2, snipe O.T.T.O's Outpost** — it awards an extra star regardless of
  damage, and gold is tiered by stars.
- **Never assume complete information.** Hidden Teslas and every trap are
  invisible until triggered, so a computed safe route is provisional. Degrade
  gracefully rather than asserting safety.

## Verification

Live phone, in this order, quoted in the summary:

1. `python3 -m coc.cli collect --dry-run` — confirm the `detect` events name the right bubbles and
   nothing was refused unexpectedly.
2. `python3 -m coc.cli collect` — quote taps, rounds, `bubbles_remaining`, and the resource delta
   from `runs/<stamp>_*/run.json`.

A flow verified only by `--dry-run` is **not** verified.
