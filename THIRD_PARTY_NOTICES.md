# Third-party notices

- **Sword Coast Stratagems 35.21** by David W. The preparation in component 200
  follows SCS's precast blocks (`caster_shared/caster_definitions.ssl`:
  `SpellPrecast`, instant cast plus `RemoveSpell`), and both components work on the
  scripts and creatures SCS installs. No SCS file or generated SCS script is
  included; the repairs read SCS's installed output at install time.
- **Icewind Dale: Enhanced Edition** by Beamdog. `CIETMWK.baf` repeats the group
  wake-up blocks of the base game's `GNTRPM1.bcs`.

  The `actors/`, `placements/` and `ini/` templates retain IWD encounter placement
  and spawn data. The additional fallback BAF blocks express those encounter rules;
  private SPL resources contain this mod's decided effects. No generated SCS AI
  script is bundled. ARE record layout follows the
  [IESDP format reference](https://gibberlings3.github.io/iesdp/file_formats/ie_formats/are_v1.htm).
