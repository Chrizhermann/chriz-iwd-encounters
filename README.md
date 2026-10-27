# Chriz IWD Encounters

Small fight upgrades for **Icewind Dale: Enhanced Edition** on top of Sword Coast
Stratagems (SCS). Written for the Chriz Easy IWD collection; install it right after
SCS.

| Component | What it does |
|---|---|
| 100 | Repairs SCS caster AI that misses some IWD:EE casters: two Shadowed Elven Clerics that end up without any AI, and a few shamans and a wizard whose melee script takes over from their spell AI (they walk up to the party and only hit it). |
| 200 | Enemy priests prepare the moment they first see the party: a self-protection on Core Rules (from Hard, SCS precasts its own), a group blessing from Hard up. They use and spend their own memorised spells, like SCS's precasts. |

Details per change, written so they can move to the Chriz script engine later:
[docs/components.md](docs/components.md).

## Install

Needs IWD:EE (built and tested on 2.7.3.0) and SCS's smarter priests (component 200)
or smarter mages/priests (component 100). Copy `chriz-iwd-encounters/` into the game
folder and run `setup-chriz-iwd-encounters` with WeiDU after SCS.

## Tests

`tests/check_install.py` reads an installed game and checks what the components
changed. It never writes to the game.

## Credits

The preparation component follows the precast pattern of David W.'s Sword Coast
Stratagems; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
