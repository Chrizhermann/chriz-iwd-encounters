# Chriz IWD Encounters

Tactical encounter upgrades, pacing improvements, and Baldur's Gate spell-rule consistency for
**Icewind Dale: Enhanced Edition (`2.7.3.0`)** on top of **Sword Coast Stratagems (SCS)**. Built
for **[Chriz Easy IWD](https://bg.chrizfader.org/iwd)**
([IWD Rules & Balance](https://bg.chrizfader.org/rules#iwd) |
[Latest Release](https://github.com/Chrizhermann/chriz-iwd-encounters/releases/latest)).

---

## Part 1 — For Players

### Highlights

- **Upgraded Boss Fights (`300`–`410`):**
  - Rebuilt signature encounters across the main campaign and expansions—all working with or
    without SCS.
  - **Belhifet (`300`):** Restores his authentic IWD/SoD `BELHIFET` sprite (`0xE256`) and voices
    over SCS's Pit Fiend swap, keeps Poquelin's transformation shockwave dispel, adds Lv-26
    Abjuration Dispel Magic, Lv 1–3 spell immunity, `+2` weapon threshold, and cornugon waves.
  - **Main Campaign (`310`–`360`):** **Yxunomei**, **Kuldahar Orog Raid**, **Joril**, **Maiden
    Ilmadia**, **The Idol**, and **Poquelin** in the Ascension Cave.
  - **Heart of Winter & Trials (`370`–`410`):** **Pomab** (Cryshal-Tirith), **Mebdinga**,
    **Icasaracht**, **Lord Maluradek**, and **The Luremaster**.
- **Trimmed Filler & Asymmetric Elite Squads (`420` & `500`):**
  - Cuts ~40–50% of repetitive trash mobs across Chapters 2–6, *Heart of Winter*, and *Trials of
    the Luremaster* while fixing infinite staircase respawns and maintaining chapter XP parity.
  - Introduces *Drasus*-style named specialist squads across Chapters 2–6 (Talonite Coven, Shadowed
    Arcane Circle, Pure Orog Shock-Guard, Frostmaiden Sisterhood, Kraken Society Operatives) plus
    a **Kaylessa** (`AR5401`) overhaul and Solonor Tower garrison.
  - Adds Gloomfrost's Frost Giant War-Shaman plaza, Sea of Moving Ice Sahuagin Royal Command, and
    fixes *Polar Bear Spirit*'s Great Roar.
- **Baldur's Gate Spell Rules on IWD:EE (`120`):**
  - Uses BG caster-level Dispel/Remove Magic checks (`50%` base, `+5%`/`-10%` per level).
  - Limits Minor Spell Deflection to levels 1–4 so *Breach* and *Pierce Magic* bypass it cleanly.
  - Prevents Spirit Armor / Mirror Image / Reflected Image stacking and lets AoE damage bypass
    Mirror Image.
  - Adds logical Web, Grease, Stinking Cloud, Spook, and Horror immunities and gives
    sequencers/contingencies/Wish the Universal school.
- **SCS Caster Repairs & Priest Sight-Prebuffs (`100` & `200`):**
  - Restores AI on broken Shadowed Elven Clerics (`SDELFCH2`) and removes/reorders overriding
    melee scripts on shamans and wizards (`100`).
  - Lets enemy priests cast memorized self-protections and group blessings on sight from Core
    Rules up (`200`).
- **Crossmod Banter Crash Protection (`110`):**
  - Ensures party banter starts only between living party members in the same area, preventing an
    `Interact` engine crash with the IWD Crossmod Banter Pack (safe with or without that pack).

### Standalone Install (After SCS)

1. Target **Icewind Dale: Enhanced Edition (`2.7.3.0`)**. **SCS** is recommended for components
   `100` and `200` (not hard-gated; all other components also work standalone).
2. Download the archive from
   **[Latest Release](https://github.com/Chrizhermann/chriz-iwd-encounters/releases/latest)**.
3. Extract `chriz-iwd-encounters/` into your IWD:EE game folder (next to `chitin.key`).
4. Run `setup-chriz-iwd-encounters` with WeiDU **after SCS** (and after the Crossmod Banter Pack
   if installing `110`), then select your components.

---

## Part 2 — Component Reference, Verification & License

### Component Reference

| ID | What it does |
|---:|---|
| `100` | **SCS Caster-AI Repairs:** Restores AI on broken Shadowed Elven Clerics (`SDELFCH2`) and removes/reorders overriding melee blocks (`GNMMGSGH`, `GNTRPM1`/`CIETMWK`, SCS general AI) above caster scripts. |
| `110` | **Crossmod Banter Guard:** Rewrites slot-to-slot `Interact` blocks in `baldur.bcs` so both partners must be alive and in the same area while preserving exact random roll weights. |
| `120` | **Baldur's Gate Spell Rules & Fixes:** BG caster-level Dispels, Minor Spell Deflection L1–4, non-stacking Mirror/Reflected/Spirit Armor, AoE Mirror Image bypass, logical Web/Grease/Stinking Cloud/Spook/Horror immunities, Universal schools. |
| `200` | **Enemy Priest Sight-Preparation:** Enemy priests cast a memorized self-protection on Core Rules (SCS precasts from Hard up; unhooked `SHELFPS1`/`CAJSHA1M` from Core up) and a group blessing from Hard/Insane up. |
| `300` | **Belhifet's Final Fight:** Restores `0xE256` `BELHIFET` sprite & voices, Poquelin shockwave dispel, Lv-26 Abjuration Dispel Magic (`CIEBELDI`), Lv 1–3 spell immunity, `+2` weapon threshold, wave pacing, and teleport fix. |
| `310` | **Yxunomei & Her Temple:** Reinforcements join on fight start, Lv-18 Abjuration Dispel Magic (`CIEYXUDI`), party-only pentagram traps, and removal of non-working IWD telekinesis loops. |
| `320` | **Orog Raid on Kuldahar:** Shared camp alert, stronger war-horn leaders (`70` HP, `2` APR, `THAC0 10`), retaliating guards, and living Arundel duplicate fix. |
| `330` | **Joril's Throne Room:** `185` HP Joril, Berserker rage, Hold Person guards, Gorg's wolves rallying, and peaceful-badge XP exploit fix. |
| `340` | **Maiden Ilmadia's Forge:** `135` HP Blackguard abilities (*Aura of Despair*, *Poison Weapon*, *Absorb Health*), gathering fire giants & drow support, dialogue-safe hostility fix. |
| `350` | **The Idol:** Cooldown-paced targeting, no *Power Word: Kill*, `225` HP anchored on plinth, rallying greater mummies & zombie lords with restored aura, badge softlock fix. |
| `360` | **Poquelin (Ascension Cave):** `310` HP, half-HP jump + *Fire Storm* + immediate wave, escape cutscene reliability and instant-death guard. |
| `370` | **Cryshal-Tirith (Pomab):** Named illusions, hit-triggered teleport/re-hide, `240` HP sentries protecting Pomab and rising again. |
| `380` | **Mebdinga's Barrow:** Timed wails without hit-fleeing, honour guard wights/drowned dead under War Cry, telegraphed *Undying Lament*, fixed difficulty gates. |
| `390` | **Icasaracht's Lair:** `650` HP dragon, `250` HP soul gem, duplicate-gem guard, and second underpriestess script fix. |
| `400` | **Lord Maluradek:** `350` HP, working animated plates, all-rooms rally below 50% HP, restored dancing beholder and immunity gloves. |
| `410` | **The Luremaster:** Opens with *Improved Invisibility*, Dimension Door escapes, working Dispel Magic, and spectral hero replacements. |
| `420` | **Main Campaign Overhaul (Chapters 2–6):** ~40–50% filler thinning, 6 asymmetric named squads (`CIE401`–`CIE427`), Kaylessa Lv 15 overhaul, Solonor Tower garrison, `AR3503` 3-wave crypt, Terikan, Tarnsen, quest/staircase-respawn fixes. |
| `425` | **Quest Kill-Counter Hotfix:** Idempotent repair component for existing installations—lowers Dragon's Eye Lv 2 (`>6`/`<7`) and Severed Hand (`>11`) thresholds and preserves `Talonite` / `ELVEN_SOLDIER` quest death variables on `AR4002` & `AR5403` squad placements. |
| `500` | **Heart of Winter & Trials of the Luremaster:** *Polar Bear Spirit* Great Roar fix, Burial Isle thinning & respawn fix, Gloomfrost Frost Giant War-Shaman plaza (`CIE5GHST`), Sea of Moving Ice & Sahuagin Royal Command, `AR9602` repair. |

Full engine-neutral specification (written so rules can move cleanly to future script-engine
builds): [docs/components.md](docs/components.md) · Change history: [CHANGELOG.md](CHANGELOG.md).

Components follow **We Overwrite**: each component writes its decided actors, fields, scripts, and
spells regardless of prior edits or mod versions.

### Verification

- `python -I tests/test_templates.py` — validates bundled CRE, placement, and spawn templates
  offline.
- `python -I tests/test_banter_guard.py <weidu.exe>` — verifies component `110` script patching
  and exact roll probabilities without a game folder.
- `python -I tests/test_overwrite.py <weidu.exe> <read-only-reference> <base|stack|edited|embedded>`
  — runs twice against disposable data-only fixtures to verify **We Overwrite** behavior cleanly.
- `python -I tests/check_install.py <game_dir>` — read-only inspection of an installed game's
  changes.

### Credits

The preparation component (`200`) follows the precast pattern of David W.'s **Sword Coast
Stratagems**. Built on **Icewind Dale: Enhanced Edition** (Beamdog) and **IESDP** format
documentation; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for full third-party notices.

### License

Licensed under the **[MIT License](LICENSE)** (`Copyright (c) 2026 Christopher Hermann`) — see
**[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)** for third-party notices and boundaries.
