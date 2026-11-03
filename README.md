# Chriz IWD Encounters

Small fight upgrades for **Icewind Dale: Enhanced Edition** on top of Sword Coast
Stratagems (SCS). Written for the Chriz Easy IWD collection; install it right after
SCS.

| Component | What it does |
|---|---|
| 100 | Repairs SCS caster AI that misses some IWD:EE casters: two Shadowed Elven Clerics that end up without any AI, and a few shamans and a wizard whose melee script takes over from their spell AI (they walk up to the party and only hit it). |
| 200 | Enemy priests prepare the moment they first see the party: a self-protection on Core Rules (from Hard, SCS precasts its own), a group blessing from Hard up. They use and spend their own memorised spells, like SCS's precasts. |
| 300 | Belhifet's final fight: immune to spell levels 1–3 only, +2 weapons hit him, fire immune as in the base game, more hit points from Core Rules up, Improved Invisibility when he appears and Haste for 30 seconds out of every 42, his cornugons come as a second wave (a third on Insane), Poquelin's transformation no longer dispels the party. Works with and without SCS. |
| 310 | Yxunomei and her temple: her three mages come when the fight with her starts and walk to the party (as in the base game only on Hard and Insane), her two champions leave the torture chamber for her side if they still live, two yuan-ti elites come into her room on Hard (three on Insane), the pentagram's traps go off only for the party, and SCS's telekinesis that IWD:EE lacks no longer costs her a round. Works with and without SCS. |
| 320 | The orog raid on Kuldahar: once one group wakes, all the orogs wake and come for the party; the three leaders charge after a war horn, a bit stronger (70 hit points, two attacks, THAC0 10); the orogs fight back against the town's defenders; no second, living Arundel on the town alarm. Works with and without SCS. |
| 330 | Joril's throne room: Joril has 185 hit points; he, his bodyguards and his guards use their Berserker rage, the bodyguards cast Hold Person; Gorg's wolves come to him when he turns hostile; no double experience for the peaceful badge. Works with and without SCS. |
| 340 | Maiden Ilmadia's forge: 135 hit points and her Blackguard abilities (Aura of Despair, Poison Weapon, Absorb Health); her fire giants gather at her side and her drow bless them; the forge no longer turns hostile before her dialogue. Works with and without SCS. |

Details per change, written so they can move to the Chriz script engine later:
[docs/components.md](docs/components.md).

## Install

Needs IWD:EE (built and tested on 2.7.3.0) and SCS's smarter priests (component 200)
or smarter mages/priests (component 100); components 300 to 340 also work without SCS.
Extract the release zip from the GitHub
releases into the game folder (it holds `chriz-iwd-encounters/`) and run
`setup-chriz-iwd-encounters` with WeiDU after SCS.

## Tests

`tests/check_install.py` reads an installed game and checks what the components
changed. It never writes to the game.

## Credits

The preparation component follows the precast pattern of David W.'s Sword Coast
Stratagems; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
