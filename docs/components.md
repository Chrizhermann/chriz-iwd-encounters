# Components

What each component changes, in terms that do not depend on WeiDU, so the same
behaviour can later move to the Chriz script engine. Spell names are SPELL.IDS
symbols. Difficulty names are the in-game slider: Easy, Normal, Core Rules, Hard,
Insane (DIFFLEV 1–5).

## 100: SCS caster-AI repairs

Needs Sword Coast Stratagems' smarter mages or smarter priests. Each repair finds its
cases from the installed files; when SCS has done the job, it changes nothing.

### Shadowed Elven Clerics without AI

- **Who:** every creature whose script slot names `SDELFCS1` while no such script
  exists. On SCS 35.21 that is `SDELFCH2`, the two Shadowed Elven Clerics that
  `AR5202.bcs` spawns in the Severed Hand.
- **Cause:** SCS's `priest/priest_iwd.tpa:109` writes `sdelfcs1`, a typo for
  `shelfcs1`, before its creature pass. The clerics keep their old spells and have no
  combat script; their other scripts only make them hostile and walk to Player1.
- **Change:** take the twin `SDELFCH1`, which SCS converted normally. Put its SCS
  caster script in the broken slot, and replace the creature's priest spells and
  slots per level with the twin's SCS selection. Only a creature that matches the
  twin in class, race, kit and levels is changed.

### Melee script above a caster AI

- **Who:** placements (area actors) and creatures where a melee AI runs before an
  SCS caster script. Melee AI means the base game's `GNMMGSGH` or `GNTRPM1`, or
  SCS's own melee AI (scripts with the global `DMWW_genai_difficulty`), which SCS's
  smarter general AI puts in their place. On SCS 35.21 with its general AI: three
  Shadowed Orc Shamans in `AR5001`/`AR5002` (`DWMESSGE`, which replaced
  `GNMMGSGH`), the Shadowed Elven Wizard in `AR5302` and the one `AR5301.bcs` spawns
  (`SDELFWZH`), both with `DWGNTR0`, SCS's melee version of `GNTRPM1`.
- **Cause:** the engine runs the first script block whose triggers hold and stops
  there, and melee blocks do not `Continue()`. The base game's `GNMMGSGH` attacks
  whatever it sees, so the caster never casts. SCS's melee AI walks to the nearest
  enemy whenever the caster is idle and attacks every round once an enemy is within
  melee range (`Range(…,4)`): the caster AI below gets turns only at a distance, and
  a caster next to the party only swings its weapon. Lab, Core Rules, SCS 35.21: the
  Shadowed Elven Wizard placed next to the party attacked in 154 of 180 samples
  (`AttackOneRound`) and cast nothing.
- **Change:**
  - a plain melee AI (`GNMMGSGH`, or one of SCS's generic melee scripts) is removed
    from the slot; the caster AI fights on its own;
  - a melee AI built from `GNTRPM1` is replaced by `CIETMWK`, `GNTRPM1`'s group
    wake-up without the melee blocks: stay deactivated until `AREA_GROUP_VARBit1`
    (MYAREA) is set, then activate and become hostile, and walk to Player1 when idle
    and no PC is in sight;
  - any other melee AI there is left unchanged and named in the WeiDU log.
- Which SCS script came from which base-game script is read from SCS's own record,
  `weidu_external/data/stratagems/genai_scripts_built.txt` (lines
  `original-base---built`).
- Slots compare in run order (SCRLEV.IDS): override, specifics, class, race, general,
  default. An area actor uses its creature's script wherever its own slot is empty;
  a plain melee AI is only removed where that leaves the slot really empty.

## 200: enemy priests prepare when they first see the party

Needs SCS's smarter priests. Christopher, 2026-10-25: "Einfach nur so, dass sie
nicht nackt sind". Graded by difficulty on 2026-10-28: "ab Core ein paar prebuffs
… bis auf Insane das Ganze dann erhöhen".

- **Who:** an enemy (`Allegiance(Myself,ENEMY)`) of a priest class (`CLERIC_ALL`,
  `DRUID_ALL`, `SHAMAN`) that sees an enemy (`See(NearestEnemyOf(Myself))`).
- **When:** the first time that happens; each part fires once per creature
  (LOCALS `CIE_SELF`, `CIE_GROUP`).
- **How:** cast instantly (`ReallyForceSpell`) and spend the memorised copy
  (`RemoveSpell`), like SCS's own precasts. The priest is ready earlier, not stronger.
- **Self-protection:** the first memorised spell of `CLERIC_BARKSKIN`,
  `CLERIC_ARMOR_OF_FAITH`, `CLERIC_DRAW_UPON_HOLY_MIGHT`. With none of them:
  `CLERIC_ARMOR_OF_FAITH` for free; every priest class can cast it.
  - SCS priests: Core Rules only. SCS precasts their self-protection itself on Hard
    and Insane (its "InsanePrep" tier means Hard and Insane with its default
    priest-prep setting; lab: Armor of Faith as `DWSP111`). If the player changed
    that SCS setting (`DMWW_priest_prep_difficulty` not 0), this part steps aside.
  - The two original priest AIs below, which SCS does not prepare: Core Rules and up.
- **Group blessing** (Hard for priest level 7 and up, Insane for every priest): the
  first memorised spell of `CLERIC_RECITATION`, `CLERIC_PRAYER`, `CLERIC_BLESS`. They
  reach every ally around the priest. `CLERIC_CHANT` is left out: in IWD:EE it stops
  the caster's spellcasting for a turn.
- **Where the rule lives:** on top of each priest's SCS caster script (where SCS's
  precasts are), and on top of the two original priest AIs SCS misses (`SHELFPS1`,
  the Shadowed Elven Priest in `AR5203`; `CAJSHA1M`, Jackal Shaman 1 in `AR9800`).
- **Not changed:** mages (SCS prepares them from Normal up), allies, Easy and Normal,
  and priests whose AI is neither an SCS script nor one of the two named above (for
  example priests that other mods add with their own scripts).
