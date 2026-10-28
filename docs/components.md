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

## 300: Belhifet's final fight

Works with and without SCS. Designed with Christopher on 2026-10-26 ("Denke der
letzte Fight sollte etwas dauern und nicht gimicky sein") and 2026-10-28 ("Es ist
kein geiles Endkampf-Design …, wenn alles gleichzeitig passiert"). The fight takes
place in `AR1105` (Easthaven, chapter 6), which the party enters once, at the end;
Belhifet (`BELHIF`, script name `EEBELHI1`) only exists from Poquelin's
transformation on. Installed on a running game, every change applies as long as the
party has not entered that area yet.

Lab-tested on 2026-10-28 and 2026-10-29 in IWD:EE 2.7.3.0 with SCS 35.21 and EEex
1.3.1, from a save in Easthaven with one level-1 character (kept alive for the
measurement), on Normal, Hard and Insane, and on Hard without this component for
comparison: his protection spell (there when he appears, gone before the death
animation), hit points, preparation, the second wave (and the third cornugon on
Insane), the transformation without dispel (every later dispel on the character came
from the area's traps, logged effect by effect), the teleport pause and the ending.
With the level 1–3 immunity (2026-10-29, his invisibility and magic resistance taken
for the test): Magic Missile (twice) and Flame Arrow did no damage, Lower Resistance
(level 5) took effect, and the spells his own scripts apply to him still worked
(protection spell, SCS's hit point bonus, invisibility, teleports). Not tested in
the game: +2 weapons and hold effects against him (the install checks cover his items
and protections), without SCS, and with a real party.

### Protections

- **Base game:** his ring `BRING` makes him immune to spell levels 1–9 and protects
  him from 44 single spells, mostly area spells that would slip past the level
  immunity. His amulet `BEHAMU` makes him immune to non-magical, +1 and +2 weapons
  and to charm, sleep, stun, poison, horror and morale effects. `MIN1HP` keeps him at
  1 hit point at least (and protects him from vorpal hits), so the area script plays
  the ending once he is below 10 hit points. SCS adds 50 % magic resistance.
- **Change:**
  - an item that carries a spell-level immunity loses it and its protections from
    single spells (the ring);
  - instead he is immune to spell levels 1–3, and keeps the item's protections from
    single spells that belong to those levels: a priest or wizard spell named by its
    SPELL.IDS number (`SPPRlnn`, `SPWIlnn`) with level 1–3 in its header. In the
    reference install 11 of the ring's 44, such as Stinking Cloud and Skull Trap; a
    Wish option and a part of a level 6 spell that carry a low level stay out.
    Christopher, 2026-10-29. Spells his own scripts apply to him pass a spell-level
    immunity (base game: SCS's level 2 invisibility worked through the ring's
    levels 1–9), so the immunity does not block his own protections;
  - every item loses its immunities to "enchanted" weapons of enchantment 2 or more
    (the amulet's +2 entry): +2 weapons hit him;
  - changed items become copies only Belhifet carries (`CIEBELI1`, `CIEBELI2`, …);
    the same rules apply to effects on the creature itself;
  - new protections against what would end the fight without taking his hit
    points: instant death, slaying, petrification, polymorph, Power Word: Kill,
    imprisonment, maze, disintegration (opcodes 13, 55, 134, 135, 209, 211, 213,
    238), and every spell that takes his hit points to the bottom in one go
    instead of dealing damage. Found at install time over all spell types (such
    effects often sit in a sub-spell): damage that sets hit points to at most a
    tenth of his own (at least 10) or to at most 10 %, or takes 90 % or more;
    current or maximum hit points set the same way (opcodes 12, 17, 18). Spells
    that only take a small share, or set hit points high, stay. In the reference
    install: the old Harm that sets hit points to 1–4, a "reduce by 100 %"
    sub-spell, and a few helper spells of other mods; Polymorph Other's polymorph
    falls under the polymorph protection;
  - protection from paralysis and hold (opcodes 109, 175, 185; IWD:EE's Hold Person
    and Hold Monster hold with 175). Christopher, 2026-10-29;
  - the protections are one spell (`CIEBELPR`: not dispellable, no secondary type
    to breach) that the script running first for him applies when he appears, so
    the ending can take them away again (below).
- **Kept:** his magic resistance and resistances, the amulet's protections from
  charm, sleep, stun, poison, horror and morale effects, the minimum hit point and
  the scripted ending.
- **SCS:** 35.21 lowers his fire resistance from 100 % to 50 % (component 6510), so
  his own fireballs and the blast of his teleport hurt him when he stands near their
  target (six hits in one lab fight, about 17 hit points per fireball). Unchanged
  here.

### Ending

- **Base game:** below 10 hit points the area script starts the cutscene `EEBELDTH`;
  with SCS his own script does the same. Both cast his death animation (`SPIN171`,
  `INNATE_BELHIFETS_DEATH_ANIMATION`: a visual and an instant death at power 10,
  which the ring's spell-level immunity never blocked), play his death sequence and
  start `EEBELKIL`, which kills the golems and cornugons and plays the end movies.
  The instant death itself does not take: `MIN1HP`'s minimum hit point makes him
  immune to directly applied instant death (IESDP, opcode 208). In the lab he stayed
  at 1 hit point while the ending played.
- **Change:** every script that casts the death animation on him first applies
  `CIEBELEN` (removes `CIEBELPR`) and waits two AI ticks, so he meets the death
  animation as in the base game, also where another mod kills him for real (for
  example after taking `MIN1HP`). Lab, Hard: the protections were gone when the
  animation started, and the ending ran.

### Hit points

- Easy and Normal: unchanged (base game 350).
- Core Rules ×10/7, Hard ×25/14, Insane ×15/7 of his installed hit points (base
  game: 500, 625, 750), rounded. Christopher, 2026-10-28: Core Rules "wesentlich
  mehr", 875 on Insane perhaps too much.
- Applied once, when he appears: a permanent raise of maximum and current hit points
  (opcode 18, mode 0), which his magic resistance does not stop. Built at install
  time as `CIEBHP3`, `CIEBHP4`, `CIEBHP5`; the rule sits on top of the script that
  runs first for him.
- With SCS: its fiend "staying power" (on Hard and Insane, or on any difficulty its
  fiend setting asks for) adds half of his hit points on top (`DW#FIEHP`: maximum
  and current hit points to 150 %, opcode 18 mode 2, renewed before it runs out).
  It multiplies the raised value: in the lab on Hard 625 became 937; Insane works
  out at 1,125.

### Preparation

- Core Rules and up: he casts Improved Invisibility on himself the moment he
  appears, instantly, like SCS's precasts. With SCS he recasts it in the fight as SCS
  intends. Christopher, 2026-10-28: he buffs before and during the fight, as SCS
  does.

### Second wave

- **Base game:** two invisible cornugons (`Cornugon_1`, `Cornugon_2`) are destroyed
  on entry below Hard, unless Icasaracht's soul gem has been destroyed
  (`SPRITE_IS_DEADGEM`, the end of Heart of Winter). During Poquelin's talk they come
  through his portal (cutscene `EECRNENT`) and fight from the first moment, together
  with Belhifet and the two iron golems.
- **Change:** where the base game keeps them, they leave when the party enters (as
  the base game has them do below Hard) and come back through the portal when
  Belhifet falls below two thirds of his hit points: copies of their creatures with
  the placements' scripts and the same script names (`CIEBELC1`, `CIEBELC2`),
  visible, at their old places by the portal, with the Gate visual (`SPSUMGTE`).
  The ending cutscene and every script that names them find them as before.
  Deactivating them while they wait is not enough: a deactivated creature keeps
  running its scripts, and in the lab the waiting cornugons teleported after the
  party.
- A cornugon whose creature cannot be copied (stored inside the area file) stays as
  in the base game and fights from the start; the installer says so.
- **Insane:** below one third, a third cornugon comes through, between the two
  cornugons' places (`CIEBELC3`: a copy of `Cornugon_1`'s creature with that
  placement's scripts, script name `CIE_CORNUGON_3`, visible). The ending cutscene
  `EEBELKIL` kills the golems and cornugons by name; it gets the same line for the
  third, and without that line the third is left out.
- The golems are unchanged.
- The rule lives in the finale area's script, stage in the area variable
  `CIE_BEL_STAGE` (1 waiting, 2 arrived, 3 third arrived, 9 none in this fight).

### Poquelin's transformation

- **Base game:** the transformation spell (`SPIN183`,
  `INNATE_FLASH_DESTROY_SUMMON_BELHIFET`) dispels everyone around Poquelin without a
  roll (opcode 58 mode 0), takes summoned weapons and magical berries from them,
  destroys illusions and shows "Dispel Effects". The cutscene `EEPOQCNG` also forces
  Dispel Magic on the nearest party member (WeiDU prints the line with
  `WIZARD_REMOVE_MAGIC`, a name that shares the spell's number on IWD:EE).
- **Change:** those effects go; so does every spell the cutscene forces on someone
  other than Poquelin that dispels (opcode 58), found by its effects, not its name.
  The transformation, its visuals and sound, and Poquelin's replacement by Belhifet
  stay. Christopher, 2026-10-28: the dispel goes.
- **Not changed:** the finale area's six proximity traps (`Trigger Point 1`–`6`,
  script `GNT2010`, detection 95, removal 100, they reset) cast `SPWI010` on whoever
  enters: a dispel without a roll (opcode 58 mode 0). Both are base game. In the lab
  a character panicked by Demon Fear ran into them 17 times in one fight.

### SCS's teleport pause

- SCS 35.21 (`fiend/ssl/bel_conveyance.ssl`; installed as the timers
  `belhifet_bel_conveyance` and `belhifet_bel_conveyance_timer`) checks one timer
  before a teleport but sets the other after it. Its 24-second pause never applies:
  he teleports whenever his 6-second spell timer has run out, and since the teleport
  blocks come before his spell blocks, those rarely get their turn. Lab, Hard, SCS
  as shipped: 34 teleports in 198 seconds (every 6 seconds on average), each with
  Demon Fear, no Fiend Fireball.
- **Change:** every timer his script sets as `<name>_timer` while it only checks
  `<name>` is set as `<name>`. Lab, Hard and Normal: his Infernal Conveyance every
  24–31 seconds (SCS's Teleport Without Error now and then on top, 18–21 seconds
  between teleports of either kind on average), Demon Fear every 6–14 seconds,
  Fiend Fireball every 6–52 seconds, melee in between. Without SCS, or once SCS
  fixes it, nothing changes (the base game teleports him on its own timers, every
  9–26 seconds).
