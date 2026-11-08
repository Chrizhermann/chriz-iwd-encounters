# Chriz IWD Encounters

Small fight upgrades for **Icewind Dale: Enhanced Edition** on top of Sword Coast
Stratagems (SCS). Written for the Chriz Easy IWD collection; install it right after
SCS.

| Component | What it does |
|---|---|
| 100 | Repairs SCS caster AI that misses some IWD:EE casters: two Shadowed Elven Clerics that end up without any AI, and a few shamans and a wizard whose melee script takes over from their spell AI (they walk up to the party and only hit it). |
| 110 | Party banter starts only between living party members in one area. Stops a crash with the Crossmod Banter Pack, whose banter could pick a dead partner. Needs no other mod and does nothing without that banter; install it after the pack. |
| 200 | Enemy priests prepare the moment they first see the party: a self-protection on Core Rules (from Hard, SCS precasts its own), a group blessing from Hard up. They use and spend their own memorised spells, like SCS's precasts. |
| 300 | Belhifet's final fight: immune to spell levels 1–3 only, +2 weapons hit him, fire immune as in the base game, more hit points from Core Rules up, Improved Invisibility when he appears and Haste for 30 seconds out of every 42, his cornugons come as a second wave (a third on Insane), Poquelin's transformation no longer dispels the party. Works with and without SCS. |
| 310 | Yxunomei and her temple: her three mages come when the fight with her starts and walk to the party (as in the base game only on Hard and Insane), her two champions leave the torture chamber for her side if they still live, two yuan-ti elites come into her room on Hard (three on Insane), the pentagram's traps go off only for the party, and SCS's telekinesis that IWD:EE lacks no longer costs her a round. Works with and without SCS. |
| 320 | The orog raid on Kuldahar: once one group wakes, all the orogs wake and come for the party; the three leaders charge after a war horn, a bit stronger (70 hit points, two attacks, THAC0 10); the orogs fight back against the town's defenders; no second, living Arundel on the town alarm. Works with and without SCS. |
| 330 | Joril's throne room: Joril has 185 hit points; he, his bodyguards and his guards use their Berserker rage, the bodyguards cast Hold Person; Gorg's wolves come to him when he turns hostile; no double experience for the peaceful badge. Works with and without SCS. |
| 340 | Maiden Ilmadia's forge: 135 hit points and her Blackguard abilities (Aura of Despair, Poison Weapon, Absorb Health); her fire giants gather at her side and her drow bless them; the forge no longer turns hostile before her dialogue. Works with and without SCS. |
| 350 | The Idol: one spell per round on cooldowns, only at targets it can affect, no Power Word: Kill; 225 hit points, it stays on its plinth; its greater mummies and zombie lords come when it is attacked; the zombie lords' aura works again, and the badge counter can no longer lock the way to Poquelin. Works with and without SCS. |
| 360 | Poquelin in the Ascension Cave: 420 hit points; below three quarters he jumps away, calls Fire Storm and the next wave comes at once; no instant death or removal skips his escape; the escape cutscenes find him. Works with and without SCS. |
| 370 | Cryshal-Tirith: Pomab's images carry his name, and after every hit on him they all jump and hide again what a revealing spell showed; they keep their distance; his sentries go for whoever attacked him and for enemies close to him, with 240 hit points; every hit on him counts, and downed sentries always stand up again. Works with and without SCS. |
| 380 | Mebdinga's barrow: her wails come on time and she no longer runs every time she is hit; the nearest barrow wight and drowned dead come to her as an honour guard (two of each on Hard and Insane), hasted by War Cry; a telegraphed Undying Lament below half her hit points on Hard and Insane; hostile before the talk she is mortal; the barrow's difficulty gates work again. Works with and without SCS. |
| 390 | Icasaracht's lair: 650 hit points for her, 250 for her soul gem; no second gem if she dies without her last cutscene; SCS's second underpriestess repaired. Works with and without SCS. |
| 400 | Lord Maluradek: his banishment rooms wake their animated plates, which now fight; 350 hit points; all rooms wake below half his hit points; the dancing beholder holds still again and he wears his immunity gloves. Works with and without SCS. |
| 410 | The Luremaster: he opens with Improved Invisibility, hops away by Dimension Door when an enemy reaches him, and his Dispel Magic works; fallen spectral heroes are replaced again. Works with and without SCS. |

Details per change, written so they can move to the Chriz script engine later:
[docs/components.md](docs/components.md).

## Install

Needs IWD:EE (target 2.7.3.0). SCS is recommended and supplies the AI repaired by
component 100 and prepared by component 200; its installation record is not a gate.
The two named original priest AIs and encounter components also work without SCS.
Extract the release zip from the GitHub
releases into the game folder (it holds `chriz-iwd-encounters/`) and run
`setup-chriz-iwd-encounters` with WeiDU after SCS.

## Tests

`tests/check_install.py` reads an installed game and checks what the components
changed. It never writes to the game. It checks the components the game's `WeiDU.log`
lists (without a log, the components whose changes it finds), so a listed component
whose changes are missing fails.

`tests/test_banter_guard.py` runs component 110's patch with real WeiDU on script text
and works out every chance as an exact fraction; it needs no game
(`python -I tests/test_banter_guard.py <weidu.exe>`).

`python -I tests/test_overwrite.py <weidu.exe> <read-only-reference> <scenario>`
builds a disposable data-only fixture inside the checkout and installs all 15
components twice. Scenarios are `base` (BIFF resources), `stack` (effective resources
with this mod's available backups restored), `edited` (changed values and missing
blocks, placements and effects), and `embedded` (area-owned creatures). It checks
the decided output and rejects WeiDU errors and warnings. No game executable runs.
BIFF and backup fixtures are snapshots, not proof of a pristine game or every stack.
`python -I tests/test_templates.py` checks the bundled binary records and spawn
sections without opening a game.

## Credits

The preparation component follows the precast pattern of David W.'s Sword Coast
Stratagems; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
