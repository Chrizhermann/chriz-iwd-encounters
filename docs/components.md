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
(protection spell, SCS's hit point bonus, invisibility, teleports). Fire (2026-10-29,
Hard): in the game his fire and magic fire resistance read 100; 20 fire and 20 magic
fire damage took no hit points, 20 electricity damage took 20 (his amulet makes him
immune to cold, so cold is no control). Hit points with SCS (2026-11-03, Hard): 625
when he appears; SCS's staying power was applied once and did not take. Haste
(2026-11-03, Hard): hasted 30.0 seconds, then 12.0 without, twice in a row; the
attacks stat read 2 per hasted half round instead of 3 per round (4 per round, as
IESDP describes; a hasted control character with 1 attack still read 1, so 2 per
round), and the ending's `CIEBELEN` took the haste away within 2 seconds before the
ending played. Not tested in the game: +2 weapons and hold
effects against him (the install checks cover his items and protections; the hold
protections are the golems' set, Christopher, 2026-10-29: no lab test needed), without
SCS, and with a real party.

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
    and Hold Monster hold with 175), set up as the game's own hold-immune creatures
    have it (base game: the golems' `IRONGOL`, `GOLSTONE`, `GOLCLA`): no "Held" or
    "Paralyzed" text and no hold animation over him. SCS gives every hold-immune
    creature the spell state `HOLD_IMMUNITY` and makes the hold spells skip creatures
    in it; he gets it too wherever `SPLSTATE.IDS` has it. Christopher, 2026-10-29;
  - immune to fire again, as in the base game: fire and magic fire resistance 100 %.
    SCS 35.21 lowers both to 50 % (improved fiends, component 6510), so his own
    fireballs and the blast of his teleport hurt him (six hits in one lab fight, about
    17 hit points per fireball). Christopher, 2026-10-29: fire immune, on theme for a
    devil;
  - protection from every spell that raises maximum hit points by a percentage
    (opcode 18, modes 2 and 5, over 100 %), so his hit points stay this component's
    final values (below). In the reference install: SCS's fiend and dragon "staying
    power" (`DW#FIEHP`, `DW#DRAHP`), Tenser's Transformation and two more spells
    (`SPWM153`, `C0APOT04`);
  - the protections are one spell (`CIEBELPR`: not dispellable, no secondary type
    to breach) that the script running first for him applies when he appears, so
    the ending can take them away again (below).
- **Kept:** his magic resistance and his other resistances, the amulet's protections
  from charm, sleep, stun, poison, horror and morale effects, the minimum hit point
  and the scripted ending.

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
- Final values, also with SCS. Christopher, 2026-11-03: 625 on Hard and 750 on
  Insane with SCS too. SCS's fiend "staying power" (on Hard and Insane, or on any
  difficulty its fiend setting asks for: `DW#FIEHP`, maximum and current hit points
  to 150 %, opcode 18 mode 2) would multiply the raised value (lab before this
  change: 625 became 937 on Hard); his protections keep it from taking. Lab, Hard
  with SCS: 625.

### Preparation

- Core Rules and up: he casts Improved Invisibility on himself the moment he
  appears, instantly, like SCS's precasts. With SCS he recasts it in the fight as SCS
  intends. Christopher, 2026-10-28: he buffs before and during the fight, as SCS
  does.
- **Haste**, Core Rules and up: normal Haste for 30 seconds, then 12 seconds
  without, again and again, free (`CIEBELHA`). Christopher, 2026-10-29 ("immer
  wieder … mit irgendeinem Cooldown") and 2026-11-03 (30 on, 12 off; Improved Haste
  all the time would be too much). Normal Haste halves his round timer and gives one
  more attack per round (IESDP, opcode 16): 4 attacks instead of 3, and faster
  movement. It looks and sounds like the game's Haste (its visual, glow, sounds,
  "Hasted" and the Haste icon) and is dispellable like it, but his immunity to spell
  levels 1–3 keeps Dispel Magic and Slow away from him, so the party can only wait
  for the pause.
- His script starts the cycle once; after that the spell casts itself again 42
  seconds later (a delayed opcode 146 that no dispel removes), independent of his
  AI. A script timer was not exact enough: in the lab his AI noticed it 2–5 seconds
  late while he was busy. The ending's `CIEBELEN` stops the cycle.

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
- **Fire:** the placed cornugons' creatures (base game `FINCOR01`, `FINCOR02`) get
  their base game fire and magic fire resistance of 100 % back; their copies inherit
  it. SCS 35.21 lowers both to 50 % and makes them immune to electricity, which
  stays. Christopher, 2026-11-03.
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

## 310: Yxunomei and her temple

Works with and without SCS. Designed with Christopher on 2026-11-03 and 2026-11-04,
after a consultation with Gemini 4 Argon on the verified facts of the fight
("nicht komplett penetrant, einfach nur das Ganze ein bisschen interessanter"). The
fight takes place in `AR4005` (Dragon's Eye, chapter 2): the Yxunomei Girl Form
(`YXUNGIRL`) talks to the party, every dialogue branch ends in `Enemy()`, and her
transformation (`SPIN182`) creates Yxunomei (`TANARRI`, script name `Yxunomei`) at
her spot. The area variable `YXUN_ATTACK` marks the real start of the fight: the
girl sets it when she turns hostile, her guards (`D5YXNATK`) when one of them is
attacked. Installed on a running game, the changes apply as long as the fight has not
started; the mages' change also needs them not to have come yet.

Lab-tested on 2026-11-04 in IWD:EE 2.7.3.0 with SCS 35.21 and EEex 1.3.1, from a save
with one level-1 character (kept alive for the measurement) brought to her room, on
Core Rules, Hard and Insane. Her archers' team saw the party at once
(`MAP_GROUP_HOSTILE5` 1.2 seconds after arrival, when the base game would have
brought the mages); the mages came 0.7 seconds after `YXUN_ATTACK`, at the end of
her dialogue. Hard and Insane: all three walked 540–700 pixels to the party and
then cast. Core Rules: they left on their first round, as in the base game. On every
difficulty both champions jumped beside her 1.1–1.5 seconds after she appeared and
fought; the High Torturer stayed neutral in the torture chamber. Hard: two elites,
Insane: three, 6.4 seconds after she appeared; Core Rules: none. Not tested in the
game: the traps and the telekinesis block (the install checks cover the scripts),
without SCS, and with a real party.

### Her mages

- **Base game:** the area script creates three yuan-ti mages (`YUANMAG`; with SCS
  `DWYUMAG5`–`7`) with the Dimension Door visual east of her door (door 12) once
  `MAP_GROUP_HOSTILE5` is set. That is her guards' team variable; her archers' team
  script sets it the moment they see the party, so the mages come long before she
  talks, and the base game's difficulty script on them (`EFDELDEF`) removes them on
  their first round below Hard unless they see a party member. They have no orders to
  look for the party.
- **Change:** the spawn waits for `YXUN_ATTACK`, and each mage's creature file gets
  `CIEYXPUR` in its override slot (the first to run; SCS's mage AI ends with a block
  that holds every idle mage): when the mage has nothing to do and detects no enemy,
  it walks to Player1. The first round only marks the mage, so `EFDELDEF` still
  decides in that round: below Hard (unless Heart of Winter is finished) the mages
  still leave, as in the base game.

### Her champions

- **Base game:** two Yuan-ti Champions (`YUCHAMP`, `CDYUCHAM`; placements
  `Yuan-Ti Champion 1`, `2`) stand with the High Torturer in the torture chamber,
  about 2000 pixels south of her, neutral until his team turns hostile.
- **Change:** once she has appeared, each champion that lives and is not charmed by
  the party moves into her guards' team (the team script of the placements that run
  `D5YXNATK`, `GNTEAM5M`; so the High Torturer's team does not turn hostile through
  it), turns hostile and jumps next to her (70 pixels left and right of where she
  appears, 40 below; Dimension Door visual). Players who cleared the torture
  chamber first face her without them. Area variables `CIE_YXU_CHAMPION_1`, `_2`.
- **"She has appeared"** is her own script's first pass, which sets the area
  variable `AREA_VARBit2` (base game and SCS); without that block, the girl's
  transformation (`YXUN_CAST_SPECIAL`). Not her name: the transformation summons her
  (opcode 67), and in the lab `Exists("Yxunomei")` stayed false while she stood
  there (asked as the party leader and as a champion).

### Elites on Hard and Insane

- One round after she has appeared (see above), if she still lives: two Yuan-ti Elites
  (`YUAEWSW`, halberd) on Hard, three on Insane, come into her room with the
  Dimension Door visual, at points of her room relative to where she appears (girl
  + 133/−102, + 223/+108, + 83/+168 pixels; walkable on the base game's map). Area
  variable `CIE_YXU_ELITES` (1 waiting, 2 arrived), timer `CIE_YXU_ELITE_TIMER`.
  Christopher, 2026-11-04: the optional step stays in.

### The pentagram's traps

- **Base game:** three trap regions in front of her (`Penta Confusion 1`, `2`,
  `Penta Paralyze`; scripts `GNT2017`, `GNT2016`) go off on `Entered([ANYONE])`, so
  her own guards trigger them when they advance on the party.
- **Change:** the trap regions within 400 pixels of where she appears run copies of
  their scripts (`CIEYXT1`, `CIEYXT2`) that go off on `Entered([GOODCUTOFF])`: the
  party, its allies and summons. The traps in the halls are unchanged.

### SCS's telekinesis

- SCS 35.21's fiend AI for her (`D5YXUN`) has a Hard-and-Insane block that casts
  `DW#BATEL`, the balor's telekinesis, at fighters and monks. SCS installs that
  spell only outside IWD:EE (`stratagems/fiend/fiend.tpa`), so the block only sets
  her one-round spell timer. While `DW#BATEL.SPL` does not exist, every block of her
  scripts that names it is removed.

### Not changed

- Her own stats, spells and AI as SCS builds them (staying power on Hard and Insane),
  her guards, the High Torturer and the High Baptist, the doors (door 12 locks with
  `YXUN_ATTACK`), the hall traps, the plot (her death variable, the Heartstone Gem,
  `YXUN_ATTACK`, the transformation chain).
- The rest of the temple. The yuan-ti scripts' last blocks (`D5YUANG`, the priests'
  `D5YUANP1`–`4` and SCS's copies) were meant to send idle yuan-ti to the party once
  `YXUN_ATTACK` is set, but a "back to my post" block with the same conditions comes
  first; in the lab the groups away from her rooms stayed where they stood. Her
  guards and the group next to her room came anyway (her guards' own script, SCS's
  calls for help). Repairing the order would send every surviving group of the
  temple to her room; Christopher, 2026-11-04: masses of enemies are not fun. Left
  as it is.

## 320: the orog raid on Kuldahar

Works with and without SCS. Designed with Christopher on 2026-11-03 ("die Orogs
bekommen eine schlichte KI und kommen auf die Gruppe zu", the Marauders "als zweite
Welle") and 2026-11-04 (no extra Marauders, "die Anführer … ein bisschen stärker":
"supi"). The raid appears in Kuldahar (`AR2100`) on the party's first visit after
Yxunomei's death: the area script's block on `SPRITE_IS_DEADYXUNOMEI` and
`#spawn_group_1` creates 7 Neo-Orog Avengers (`KAOROG`), 3 Neo-Orog Marauders
(`KAOROGE`) and 8 defenders (`KATOWN1`–`3`, neutral townspeople who attack orcs) in
five places of the town. No SCS AI runs on them. The component reads the raid from
that block: raiders are the creatures whose default script is `KUATKORO`, the leaders
those of them with the most experience.

Lab-tested on 2026-11-04 in IWD:EE 2.7.3.0 with SCS 35.21 and EEex 1.3.1 on Hard, from
a save with one level-1 character brought to Kuldahar right after Yxunomei's death
(`SPRITE_IS_DEADYXUNOMEI` 1), once at the east entrance and once in the middle of the
town. The alert came 2.4–2.9 seconds after the raid appeared; all seven Avengers (45
hit points) walked 190–1780 pixels to the party; the war horn sounded 18 seconds
later; the three Marauders (70 hit points, 2 attacks, THAC0 10) waited for it unless
the party or a defender reached them first, then charged. In the middle of the town
the defenders near the party woke and attacked the Marauder beside them. Not tested
in the game: the town alarm's Arundel, the four-day cleanup, without SCS, and with a
real party.

### The raid moves as one

- **Base game:** every raider and defender stands still (`KUATKEFF`, a last block
  `True()` → `NoAction()`) until a party member comes within range 35 or it is
  attacked; then it switches to `KUATKREM` (cleanup only) and its default script
  takes over. The orogs (`KUATKORO`) attack enemies they see and walk to an attacker;
  they never look for the party, so each group waits for the party to come to it.
- **Change:** the first raider or defender that wakes sets the area variable
  `CIE_KUL_ALERT` (top of `KUATKREM`). The Avengers' creature files run `CIEKULAV`, a
  copy of `KUATKEFF` that also wakes them with the alert. Awake orogs with nothing to
  do that see no enemy walk to Player1 (end of `KUATKORO`).
- The defenders keep `KUATKEFF` and its rule (they wake when the party comes close or
  attacks them). In the lab a defender far from the party never ran its script: with
  the alert set and every condition of a wake block true (checked as that defender
  12 and 55 seconds after the alert), it stayed asleep, while the Avengers as far away
  woke and walked.

### The leaders as a second wave

- The Marauders' creature files run `CIEKULMA`, a copy of `KUATKEFF` that wakes them
  when `CIE_KUL_WAVE` is 2 instead of with the alert. Three rounds after the alert
  (`CIE_KUL_WAVE_TIMER`), the area script plays the war horn (`S_HORN`, heard all
  over the map) and sets it. A Marauder the party reaches or attacks first still
  fights at once, as in the base game.
- **Stronger:** Marauders 70 hit points (base game 42), 2 attacks per round (1),
  THAC0 10 (12); Avengers 45 hit points (31). Values are only raised, never lowered.

### Repairs

- **The defenders:** they attack orcs on sight, but are neutral, so the orogs never
  fought back. Awake orogs now attack whoever neutral attacks them. They still leave
  the other townsfolk alone (those only flee).
- **Raiders who never woke:** woken raiders leave four days after the raid's first
  visit (`KUATKREM`: `OnCreation`, `2100_ATTACK` expired); the asleep script lacked
  that block, so groups the party never met stayed until chapter 3. `KUATKEFF` and
  both copies get it.
- **A second Arundel:** the town alarm (`KULDAHAR_ALARM`, when the party attacks
  townspeople) creates Arundel outside his house (`ARUNDEL1`). After Yxunomei's death
  he is dying upstairs (`AR2112`), so that block now also needs
  `SPRITE_IS_DEADYXUNOMEI` 0.

### Not changed

- The raid's places and size, the defenders' own AI and wake rule, the fleeing
  townsfolk, the plot (Arundel's house, `KULDAHAR_FORCEREMOVE`, `2100_ATTACK`, the
  town-hostility chain), the music.

## 330: Joril's throne room

Works with and without SCS. Designed with Christopher on 2026-11-03 and 2026-11-04
(no Flame Blade: "jo besser so"; the rage as the kit has it: "jo"; Gorg's pack: "Wäre
das nicht das, was Sinn machen würde im Game?"). The court of Wyrm's Tooth (`AR7004`,
chapter 5): Joril (`JORIL`), two bodyguards (`GIANTFS`) and three to six guards
(`GIANTFG`) run `WTGIANT1`; ten frost giants elsewhere in the area turn hostile with
them (`MAP_GROUP_1_HOSTILE`). SCS gives Joril, the bodyguards and the guards the
Berserker kit, but its IWD melee AI has no rage block.

Lab-tested on 2026-11-04 in IWD:EE 2.7.3.0 with SCS 35.21 and EEex 1.3.1 on Hard, from
a save with one level-1 character brought next to Joril: Joril had 185 hit points,
both bodyguards cast Hold Person in the first two seconds, Joril, the bodyguards and
the guards that reached the party raged (15 extra hit points each), the guard far
away did not. Gorg turned hostile on command; his eight wolves walked towards him at
once (and, in that run, stayed neutral on the way: their own team script did not run
that far from the party, so the component now turns them hostile with the same order).
Not tested in the game: the badge experience, without SCS, and with a real party.

- **Hit points:** Joril 185 (base game 145). Only raised.
- **The court:** on top of `WTGIANT1` (only the court runs it): a creature that has
  Hold Person memorised (the bodyguards; no script of theirs cast it) casts it once at
  the enemy it sees, unless that one is helpless; a Berserker (`Kit(Myself,BERSERKER)`)
  uses the kit's rage (`BERSERKER_RAGE`) once when an enemy is within range 10. In
  IWD:EE the rage lasts a turn: +2 to hit, damage and AC, immunity to charm,
  confusion, fear, feeblemind, hold, imprisonment, level drain, maze, stun and sleep,
  and some extra hit points. Without SCS they have no kit and no rage. The bodyguards'
  Flame Blade stays unused: it would replace their giant weapon (2d10) with a 1d4+4
  fire blade.
- **Gorg's pack:** when Gorg (`WTGORG`) is hostile, he sets his pack's group variable
  `MAP_GROUP_HOSTILE1` and `CIE_JOR_GORG`; the area script then turns the eight placed
  winter wolves of the pack (`WINWOLFP`, Winter Wolf 9–16) hostile and sends them to
  him. In the base game they only turned on their own or when Joril died.
- **The badge:** the area script pays `Level_10_AVERAGE` when the party has Joril's
  badge; his dialogue pays the same when he hands it over peacefully (`DJORIL`,
  `Got_Joril_Badge` 1). The payment moves into its own block that also needs
  `Got_Joril_Badge` 0; the badge block keeps the rest (`JORIL_BADGE`, the text).

## 340: Maiden Ilmadia's forge

Works with and without SCS. Designed with Christopher on 2026-11-03 and 2026-11-04 (her
Blackguard abilities: "wäre das nicht cool?"; no fire elementals from the lava). The
Great Forge (`AR8011`, Lower Dorn's Deep): Maiden Ilmadia (`ILMADIA`, an elf warrior;
SCS makes her a level-12 Blackguard paladin), nine fire giants (`GIANTFIR`,
`GIANTFI2`), on Hard and Insane two drow priest-mages (`DROWPM`, `DW#DRPM2`), and
elementals and salamanders. Her dialogue always ends in `Enemy()`; the giants' group
(`MAP_GROUP_HOSTILE2`) turns with her.

Lab-tested on 2026-11-04 in IWD:EE 2.7.3.0 with SCS 35.21 and EEex 1.3.1 on Hard, from
a save with one level-1 character brought next to her house: the probe clicked through
her dialogue; 0.7 seconds after she turned hostile all nine fire giants and both drow
turned hostile, and the giants walked 170–1350 pixels to her; she had 135 hit points
and used Poison Weapon twice, five rounds apart. Not seen in the lab: Aura of Despair
(needs two enemies close; the save has one character) and Absorb Health (she stayed
above half her hit points). Also seen: the drow's area spells hit the giants crowding
around the character (SCS's casting, not this component). Not tested in the game: the
team move and the name repair (the install checks cover them), without SCS, and with a
real party.

- **Hit points:** Ilmadia 135 (base game 102). Only raised.
- **Blackguard:** on top of her script, while she has the kit
  (`Kit(Myself,BLACKGUARD)`): Aura of Despair (`SPCL103`) once when two enemies are
  within range 10; Poison Weapon (`SPCL423`) up to three times, five rounds apart,
  when an enemy is within reach; Absorb Health (`SPCL102`) once below half her hit
  points, at the enemy she sees. The kit's own table gives a level-12 Blackguard these
  uses (`CLABPA06`); no script of hers used them.
- **Her giants gather at her side:** once she is hostile, the area script turns her
  fire giants and drow (placed by name) hostile and sends the giants to her
  (`CIE_ILM_RALLY`); their own scripts take over when they see the party. Ordered from
  the area script, because far neutral creatures did not run their own scripts in the
  lab (component 320).
- **The drow bless the giants:** component 200 gives them their group blessing (Bless,
  Hard and Insane, where they exist); without it, this component gives their scripts
  the same once-only Bless.
- **Repairs:** SCS 6020's group for two salamanders and two water elementals got team
  ID 2 (`GNTEAM2M`), whose variable `MAP_GROUP_HOSTILE2` is the fire giants' switch, so
  meeting them turned Ilmadia and the giants hostile before her dialogue; they move to
  the first free team script (`GNTEAM3M` in this install). SCS's giant script checks
  `Dead("Maiden_Ilmadia")`, a name that does not exist; it now names her.

## 350: the Idol

Works with and without SCS. Designed with Christopher on 2026-11-03 ("fairer rather than
harder") and 2026-11-04 (only the undead around it come; no healing from the brothers).
Poquelin's temple (`AR8012`, Lower Dorn's Deep): the Idol (`IDOL`, `LDIDOL`, invisible
over its statue, no weapon) holds the brothers of Ilmater in thrall; around it stand six
greater mummies (`MUMMYG`) and five zombie lords (`ZOMBIEL`), in the corners 24
boneguards. Its death frees the brothers and kills every undead.

- **Casting:** the base game force-casts at the nearest enemy every three seconds, at
  random: Finger of Death 12.5 %, Power Word: Kill 12.5 % (no saving throw), Sol's
  Searing Orb, Flesh to Stone and Flame Strike 25 % each, with no regard for what the
  target is. That block goes. On top of its script: one spell per round
  (`CIE_IDOL_CAST`), each on its own cooldown — Finger of Death and Flesh to Stone
  four rounds, Sol's Searing Orb two — at the nearest or else the second-nearest enemy
  it sees, only where the spell can work: Finger of Death not at undead or summoned
  creatures, Flesh to Stone not at petrified ones, the fire spells not at fire-immune
  ones. Flame Strike (three rounds) only when its ability for the Idol's caster level
  has effects: with SCS's caster-level abilities (component 2000) plus Tweaks
  Anthology's save penalties, those of levels 2 and up have none, so it is left out.
- **Hit points and place:** 225 (base game 150); movement rate 0 (opcode 126), so it
  never leaves its plinth.
- **The rally:** when the Idol is attacked or hurt, its script sets `CIE_IDOL_RALLY`;
  the area script sends the placed greater mummies and zombie lords to its place once.
  The boneguards stay in their corners.
- **Repairs:**
  - The zombie lords' aura: their creature's race script `ZLAURA` casts it, but their
    placements put `LDIDLKIL` ("die with the Idol") in the race slot, which wins; that
    script moves to the placements' free class slot.
  - The way to Poquelin: the six badge doors' script (`LDBDGDOR`) adds 1 to
    `ALL_KEYS` when a door is unlocked and again when it is opened (and on every
    opening), and the hidden door (`LDBDGOPN`) opens only at exactly 6, so two counts
    in one pass could step past 6 for good. Each badge door gets its own copy
    (`CIEBDG1`–`6`) that counts it once (`CIE_IDOL_DOOR_n`); the hidden door opens at
    6 or more.
- **Not changed:** the boneguards and their respawns, the mummies' own casting (their
  Flame Strike has the same empty abilities), the brothers.

Lab-tested on 2026-11-04 in IWD:EE 2.7.3.0 with SCS 35.21 and EEex 1.3.1 on Hard, from a
save with one level-1 character: in front of the Idol it cast Finger of Death, Flesh to
Stone, Sol's Searing Orb, Finger of Death, Flesh to Stone at 6.4, 6.4, 11.7 and 6.5
seconds apart (the gap is the cooldowns), nothing else, from its plinth, with 225 hit
points. With the character far away, 10 damage to it set the rally within a second,
and all eleven greater mummies and zombie lords walked from their places to it. Not
tested in the game: the aura and the badge doors (the install checks cover them),
without SCS, and with a real party.

## 360: Poquelin in the Ascension Cave

Works with and without SCS. Designed with Christopher on 2026-11-03 and 2026-11-04
("Prozent, das finde ich gut"; Fire Storm after the jump: "fände ich auch nicht
schlecht"). The cave (`AR8013`, end of Lower Dorn's Deep): Poquelin (`POQUELIN`,
placement `ReveredBroPoquelin`, script `LDPOQUE1`; Belhifet in disguise) talks, turns
hostile, force-casts Heavenly Inferno and jumps to `[817.551]`; two bronze sentries and
five waves of five creatures follow, 20 seconds apart (`AR8013.BCS`). Below half his hit
points he escapes: the movie `RETURN` plays and the party is moved to Easthaven.

- **Hit points:** 420 (base game 250): the escape comes after 210 damage instead of
  125, so his waves and spells come into play. On a copy of his creature (`CIEPOQ`) for
  this cave only: the finale in Easthaven places the same creature file, unchanged.
- **The jump:** once between three quarters and half his hit points, a Dimension Door
  to the other of his two places (where he stands and where his opener jumps to), then
  Fire Storm around himself (he is immune to fire). His script sets `CIE_POQ_WAVE`; the
  area script ends the pause before the next wave (`SPAWN_TIMER` to 0), only between
  waves and while waves are left. The sequence cannot be interrupted: otherwise his
  own script takes over once he has jumped (the first lab run saw his Heavenly Inferno
  instead of the Fire Storm).
- **Repairs:**
  - His minimum hit point (`MIN2HP`) stops damage, not instant death: dying outright
    skipped the escape and the move to Easthaven. `CIEPOQ` is protected from opcodes
    13 (instant death), 55 (slay), 134 (petrification), 209 (Power Word: Kill), 211
    (imprisonment) and 238 (disintegration).
  - The escape cutscenes (`LDPOQUEB`, `LDPOQUEC`) centred the view on and deactivated
    `"POQUELIN"`, his creature's script name; his placement names him
    `ReveredBroPoquelin` (EE Fixpack shortened the actor name). They now use it.

Lab-tested on 2026-11-04 in IWD:EE 2.7.3.0 with SCS 35.21 and EEex 1.3.1 on Hard, from a
save with one level-1 character: 420 hit points. Damage to 290 (69 %) right after the
first wave's spawn window: 0.6 seconds later he cast Dimension Door, landed at his other
place, cast Fire Storm (SCS's fire cloud appeared next to him), and the second wave came
2.3 seconds after the damage instead of about 15 seconds later. Damage to 190 (45 %)
started his escape. Not tested in the game: without SCS, with a real party, the
protections (the install checks cover them).

## 370: Cryshal-Tirith

Works with and without SCS. Designed with Christopher on 2026-11-03 and 2026-11-04 (the
package without the optional sentry recall). The tower room (`AR1103`, the last fight
before Belhifet): the shopkeeper Pomab reveals himself, and a cutscene creates the real
Pomab (`EEPOMAB`, script name `PomabR`) and five images (`POMIMG1`–`5`) on one spot; four
Cryshal Sentries (`SENTRY`, ice golems) turn hostile. Each time the real one takes
damage, the area script removes an image (`SPRITE_IS_DEADFAKE_POMAB`); after the fifth
he drops to 25 hit points, loses his minimum hit point and runs; his death opens the
exits and kills the sentries. Revealing spells (Detect Illusion, True Seeing, Oracle,
True Sight) lift the images' illusion: they turn translucent and glow (`OHPOMREV`).

- **A true shell game:**
  - The images carry the real Pomab's name (base game: "False Pomab", which gave the
    real one away).
  - Each counted hit: a block on top of the area script (`CIE_POM_SHUFFLE`, set by the
    counting blocks) heals him fully, lifts a reveal from him and every image left
    (`CIEPOMRC`: opcode 321 removes `OHPOMREV`'s effects; `CIEPOMIL`, his illusion
    spell aimed at its target, makes them illusions again) and makes them all jump,
    each to another of his nine points (nine arrangements, one picked at random). Their
    scripts let them be revealed again (`POMAB_ILLUSION` back to 0 once Detect
    Illusions is 20 again) and give the images his name back.
  - Between shots they keep their distance: an enemy within 8 makes them run before
    they wander to a point.
- **The sentries guard him:**
  - They go for whoever last attacked him, then, while an enemy is within 10 of him
    (`CIE_POM_PRESSED`, from his first script so it runs in every phase), for the
    enemy nearest to him; otherwise their own targeting runs; with nothing to do they
    return to him.
  - 240 hit points (base game 100, 160 with Tweaks Anthology's maximum hit points) on a
    copy of their creature (`CIESENTR`) for this room.
  - From Core Rules up they play dead for 10 seconds instead of 20.
- **Repairs:**
  - His own full heal could come before the area script had counted the hit, so a hit
    sometimes removed no image. His script no longer heals him; the shuffle does, after
    the count.
  - His script read `FAKE_POMAB_DEAD`, a variable nothing sets, instead of the image
    counter.
  - A sentry healed while it played dead stayed down for good (its wake-up also checked
    for fewer than 10 hit points); it now stands up when its time is up.
  - The sentries' target list had the nearest enemy inside the same OR as the caster
    checks, so it always won; the casters now come first.
- **Not changed:** his wand, the taunts, the images' own heal and jump when they are
  hit, the panic at the end, the exits and the doors.

Lab-tested on 2026-11-04 in IWD:EE 2.7.3.0 with SCS 35.21 and EEex 1.3.1 on Hard, from a
save with one level-1 character, two runs: all six showed the name Pomab. Each of five
hits on the real one was counted (an image gone 1.2 seconds after the hit), and one
second later he was back at full hit points and he and every image left had jumped to
other points. After a reveal on all of them (what Detect Illusion does) the images
turned translucent; the next hit's shuffle made all of them illusions again, took the
translucency away, and their scripts let them be revealed again within a second. Both
Pomab and the images ran from the character next to them between shots. After the fifth
hit he had 25 hit points and no minimum hit point; his death killed the four sentries.
The sentries had 240 hit points; one knocked down to 5 and healed to 65 while playing
dead stood up 10.7 seconds after it went down, at full hit points; after the character
attacked Pomab the sentries saw his last attacker, and the pressed signal followed the
character's distance to him. Not tested in the game: without SCS, with a real party
(who the sentries pick between several characters), the revealing spells themselves.

## 380: Mebdinga's barrow

Works with and without SCS. Designed with Christopher on 2026-11-03 and 2026-11-04 (the
package; the Lament below half on Hard and Insane, "gerade bei höheren
Schwierigkeitsstufen"; the honour guard from the barrow's own undead, no new spawns;
the spawn file's gates back). The barrow (`AR9400`, under the Burial Isle in Heart of
Winter): Mebdinga (`MEBDING`, a spectre; talk `OHMEBTLK`, floating lines `BAMEBD`, wails
`BAMEMBA`, team `GNTEAM2M`) stands at Wylfdene's tomb. Her minimum hit point (`MINHP1`)
goes once the party has talked to her and knows of the soul (`Know_Soul`). Her wails
burst around herself: Mournful Wail (stun), Undying Lament (4d10 magic damage), Death
Knell (instant death). Wailing virgins, barrow wights and drowned dead fill the barrow
in teams.

- **Her wails come on time:** her wail script shared the timer `#localtimer` with her
  floating lines, which set it to 16–18 seconds while she saw the party; it has its own
  now (`CIE_MEB_WAIL`). Her lines stop once she is hostile. She runs from an attacker at
  most once every three rounds (`CIE_MEB_RUN`), so she stays where her wails reach the
  party.
- **Honour guard:** when her team turns hostile (or she does), the barrow wight and the
  drowned dead placed nearest to her (named, without a difficulty gate) join her team
  (her team scripts in place of theirs, so their own teams stay calm), turn hostile and
  come to her; on Hard and Insane the next wight and drowned dead as well. In the base
  game that is Barrow Wight 3 and Drowned Dead 2, then Barrow Wight 2 and Drowned Dead 7.
- **War Cry:** she sends her War Cry (haste for 18 seconds, only for male allies) once,
  to a male ally that is not hasted. The wailing virgins (`BAWAIL0`) sent theirs to the
  nearest hostile creature not in `STATE_NORMAL` (which is 0, so to anyone, mostly to
  other virgins it cannot affect); now only to a male ally that is not hasted yet.
- **Lament below half (Hard and Insane):** once she can die and is below half her hit
  points, she shows it (her hit visual `WVHITH` and "There is no water pure enough to
  cleanse this stain!"), stands for a round and then lets out an Undying Lament.
- **Repairs:**
  - Hostile before the talk (the tomb's trap or an attack on her team turns her team
    hostile), she kept her minimum hit point for good and the party never learned of
    the soul. Now she loses it once hostile, and `Know_Soul` is set as by the talk.
  - SCS 6020 writes its team script into `script_override` of spawn file entries and so
    replaced 10 of the base game's 13 difficulty gates in `AR9400.INI` (`EFDELINS`,
    `EFDELEAS`, `EFDELHRD`): those virgins, drowned dead and a wight spawned on every
    difficulty. Each such entry now runs a script that does the gate first and then what
    stands there (`CIEMG1`, `CIEMG2`, …).
- **Not changed:** the virgins' own wails and numbers, her Death Knell, her talk and the
  tomb, and the `EndCutSceneMode()` that EE Fixpack removed on purpose before her
  re-talk (a cutscene that ends right before a dialogue leaves two ticks for other
  actions).

Lab-tested on 2026-11-04 in IWD:EE 2.7.3.0 with SCS 35.21 and EEex 1.3.1 on Hard, from a
save with one level-1 character, two runs: on arrival the seven Insane-only spawns of the
spawn file were gone within a second (four of them had lost their gate to SCS). Hurt from
afar, she turned hostile and, within 1.2 seconds and without a talk, lost her minimum hit
point and set `Know_Soul`; Barrow Wight 3 and Drowned Dead 2, then (Hard) Barrow Wight 2
and Drowned Dead 7 walked 400–580 px to her and stood beside her. Once the character
stood next to her: War Cry on Drowned Dead 2, then Undying Lament, Mournful Wail and
Mournful Wail 6.5 and 7.5 seconds apart; the virgins' War Cries hasted Barrow Wight 3 and
two more drowned dead. Hurt below half, she called out at once and let out her Lament 6.2
seconds later. Not seen: her running away (the character, stunned by her wails, hardly
attacked her). Also seen: hostile or not, she still starts her talk once the party comes
close to her, so the base game kept her immortal only for a party that fought her from
afar. Not tested in the game: without SCS, with a real party.

## 390: Icasaracht and her soul gem

Works with and without SCS. Designed with Christopher on 2026-11-03 and 2026-11-04 (the
package without the optional summons; no extra wave when the gem wakes). Icasaracht's lair (`AR9604`, the end of Heart of Winter): after
her talk the white dragon fights with her sahuagin court (king, high priestess, two
underpriestesses, four guards). At her last hit point (`MINHP1`) her death cutscene wakes
her soul gem (`DLSGEM`, script name `GEM`), which summons Vodyanoi; its death ends Heart
of Winter.

- **Hit points:** Icasaracht 650 (base game 400; SCS's dragon hit point boost exists but
  nothing applies it), the soul gem 250 (150).
- **Not restored: the court's healing.** In the base game the whole court healed
  Icasaracht, the gem, the king, the guards and each other with Cure spells; SCS's
  priest lists have none. The decided capped return (the high priestess's four Cure
  spells, only on Icasaracht and the gem) does not work in IWD:EE: in the lab her Cure
  Critical and Cure Serious Wounds landed on Icasaracht without raising her hit points
  (also when applied directly), the Cure spells do not work on golems or undead (the
  gem is a golem), and the gem stays invisible, so she cannot target it.- **Repairs:**
  - Should Icasaracht die without her last-hit-point cutscene, the area script's
    fallback created a second gem next to the first (created on the first visit) and its
    cutscene ran `EquipItemEx("RING91",0)` on the gem. With the gem there, the fallback
    now runs its cutscene without a second gem, and the cutscene fills the gem's ring
    slot as the normal path does (`FillSlot(SLOT_RING_RIGHT)`).
  - The second underpriestess (SCS's copy `DWSARU0`) lacked the random items SCS gives
    the first (`DW#RND04`, `DW#RND24`); it gets the ones it lacks. Both had five attacks
    per round (a typo in the base game's creature); now one.
- **Checked in the lab, not changed:**
  - At her last hit point, `Kill(Myself)` kills her although SCS makes her immune to
    opcode 13 (she died 1.2 seconds after the gem woke).
  - Wing Buffet's opcode 13 row (death, no save) kills nobody: its effects on a level-1
    character without any protection (and 500 extra hit points) did their damage and
    stun, no death.
  - When the gem wakes it summons six Vodyanoi within four seconds on Hard (SCS's gem
    script).

## 400: Lord Maluradek

Works with and without SCS. Designed with Christopher on 2026-11-03 and 2026-11-04 (the
package, "Klingt gut"; the optional spectral guards dropped, they only add enemies). The
upper floor of the Luremaster's keep (`AR9712`): Lord Maluradek (`LORDM`, a lich,
fighter/mage/cleric; script `KELRDMAL`) talks, turns hostile and fights by banishing the
nearest enemy to one of three rooms (`SPIN140`, save vs spell -5) or force-casting a
spell each round. He fights in melee only once all three rooms have raised their alarm
(`TELEPORT_1`–`3`). The area script spawns four animated plates (`KEANIMPH`, `KEANIMP2`)
for rooms 1 and 2 once their alarm is set.

- **His banishments work:** room 3 set its own alarm, but rooms 1 and 2 waited for their
  plates, which only the alarm brings, so the rooms stayed empty, he banished people to
  them again and again and never fought in melee. A banishment to room 1 or 2 now sets
  that room's alarm (in his script, as room 3 does), so its plates appear.
- **The plates fight:** they had a script that only plays their arrival and raises the
  alarm; they get SCS's melee script (`DWMESSGE`, else the base game's `EFATKMEL`) in a
  free slot.
- **Hit points:** 350 (base game 250).
- **Below half his hit points,** at the latest, all three rooms raise their alarm: the
  plates still missing appear and come for the party, and he fights in melee between his
  spells.
- **Repairs:**
  - SCS put its beholder script (`KEBEHLD1`) in a slot that runs before the first
    beholder's dance script (`KEBEHLDD`), so the beholder could act during the dance; the
    two swap places again.
  - His immunity gloves (`CIIGEN`: charm, hold, paralysis, sleep, horror) sat in a quick
    slot, where an item does nothing (lab: paralysis held him); he wears them now.
- **Not changed:** his spells and banishment chances, the spectral guards and courtiers,
  the beholders' own scripts. Seen in the lab: three of the four room-1 plates stayed
  invisible while they fought (their own arrival script, from SCS, did not end the
  invisibility they are created with).

Lab-tested on 2026-11-04 in IWD:EE 2.7.3.0 with SCS 35.21 and EEex 1.3.1 on Hard, from a
save with one level-1 character: after his talk he banished the character to room 1;
`TELEPORT_1` was set and its four plates appeared within a second, walked about 700 px
and attacked. A banishment to room 3 set `TELEPORT_3` as in the base game. Hurt to 177
of 377 hit points, he raised all alarms: room 2's four plates appeared at once and came
for the character. With `CIIGEN` in the quick slot a paralysis held him; with the gloves
worn it did not. A second run banished the character to room 2, which set `TELEPORT_2`.
Not tested in the game: the dance and the beholders, without SCS, with a real party.

## 410: the Luremaster

Works with and without SCS. Designed with Christopher on 2026-11-03 and 2026-11-04 (the
package, "Können wir so machen"; the optional guard call dropped). The main hall of the
keep (`AR9711`): at the last meeting the Luremaster (`TRGBARD`, a level-20 bard; scripts
`DULURTLK`, `DULURMST`) fights with spectral heroes beside him. SCS's Smarter Mages took
his hop script (`DULURWRP`, a Dimension Door after every spell) off and left his class
slot pointing at a missing `NULL.BCS`; since then he stands at his throne.

- **He opens with Improved Invisibility** (memorised) once the fight starts.
- **He hops away when cornered:** while he has spells and is not beaten, an enemy next to
  him makes him Dimension Door to one of the eight points of his old circuit, every 12
  or 18 seconds at most (`CIELURHP`, in the slot that pointed at `NULL.BCS`).
- **Repairs:** his spell script's Dispel Magic entry checked `WIZARD_REMOVE_MAGIC` (2302,
  Remove Magic in IWD:EE), which he does not memorise, so his three Dispel Magic
  (`SPWI323`, 2323) never came; the entry checks and casts 2323 now.
  A fallen spectral hero now brings its replacement: the area script spawns one of six
  (`TRSPH4`–`9`) while `AR9711_HERO` is above 0, and nothing raised it (the engine only
  counts `SPRITE_IS_DEADAR9711_HERO`, the heroes' shared death variable); a block on top of
  the area script turns each new death into one replacement.
- **Not changed:** his spells, his end at 10 hit points.

Lab-tested on 2026-11-04 in IWD:EE 2.7.3.0 with SCS 35.21 and EEex 1.3.1 on Hard, from a
save with one level-1 character (`Master_Quest` set to 5): the fight started after his
talk, he was invisible 1.1 seconds later, and with the character next to him he cast
Dimension Door and landed at one of his points ([604.826]). Before the hero fix, killing
`TRSPH1` raised only `SPRITE_IS_DEADAR9711_HERO` and no replacement came; with it,
`TRSPH4` appeared 1.5 seconds after `TRSPH1` died and `TRSPH5` after `TRSPH2`. Not tested
in the game: his Dispel Magic (the install checks cover it), without SCS, with a real party.
