# chriz-iwd-encounters

Christopher's own WeiDU mod for Icewind Dale: Enhanced Edition: small fight
upgrades on top of Sword Coast Stratagems, installed right after SCS in the Chriz
Easy IWD collection (`chriz-bg-collection`, recipe `recipes/iwd-current`).

- Target: IWD:EE 2.7.3.0. Test only in disposable labs, never in Christopher's own
  game or in a read-only reference install; follow the `bg-modding` skill
  (compatibility policy, `bg-labs.md`).
- Christopher designs fights. Scope so far (2026-10-25/28): enemy casters "nicht
  nackt", graded by difficulty, quick to build; SCS defects found on IWD:EE are
  repaired here. Upgrades of single encounters come later and are designed with him.
- Describe every change in `docs/components.md` in engine-neutral terms, for a later
  move to the Chriz script engine.
- Reuse SCS ideas, not SCS files; credit them in `THIRD_PARTY_NOTICES.md`.
- No in-game technical notices; diagnostics go to the WeiDU log.
- Public release, tags and a GitHub repository only with Christopher's OK.
- Build release zips with `python -I tools/make_release.py <tag> <zip>`. The collection
  recipe pins each zip's length and SHA-256: never replace a published asset, release a
  new version instead.
