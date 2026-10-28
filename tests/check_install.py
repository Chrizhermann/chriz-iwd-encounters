"""Check what chriz-iwd-encounters changed in an installed IWD:EE game (read-only).

Usage: python -I tests/check_install.py <game_dir>

Reads the game's resources (override first, then the BIFF files chitin.key lists).
Prints one line per check and exits 1 if any check fails.
"""
import os
import re
import struct
import sys

PRIEST_TYPE = 0
CRE_TYPE, ARE_TYPE, BCS_TYPE, ITM_TYPE, SPL_TYPE, IDS_TYPE = 0x3F1, 0x3F2, 0x3EF, 0x3ED, 0x3EE, 0x3F0
EXT = {CRE_TYPE: "CRE", ARE_TYPE: "ARE", BCS_TYPE: "BCS", ITM_TYPE: "ITM", SPL_TYPE: "SPL", IDS_TYPE: "IDS"}
# 300: what Belhifet must be protected from (opcode 101 targets)
BELHIFET_BLOCKED = (13, 55, 134, 135, 209, 211, 213, 238)
# script slots by run order (SCRLEV.IDS): override, specifics, class, race, general, default
ARE_SLOTS = (0x50, 0x78, 0x60, 0x68, 0x58, 0x70)
CRE_SLOTS = (0x248, None, 0x250, 0x258, 0x260, 0x268)


class Resources:
    """override/ wins over the BIFF files listed in chitin.key (KEY V1, BIFF V1)."""

    def __init__(self, game):
        self.game = game
        self.override = {}
        for entry in os.scandir(os.path.join(game, "override")):
            stem, ext = os.path.splitext(entry.name)
            self.override[(stem.upper(), ext[1:].upper())] = entry.path
        with open(os.path.join(game, "chitin.key"), "rb") as f:
            key = f.read()
        nbif, nres, obif, ores = struct.unpack_from("<4I", key, 8)
        self.bifs = []
        for i in range(nbif):
            _, noff, nlen, _ = struct.unpack_from("<IIHH", key, obif + 12 * i)
            self.bifs.append(key[noff:noff + nlen].split(b"\0")[0].decode("latin-1").replace("\\", "/"))
        self.biffed = {}
        for i in range(nres):
            o = ores + 14 * i
            rtype, loc = struct.unpack_from("<HI", key, o + 8)
            if rtype in EXT:
                name = key[o:o + 8].split(b"\0")[0].decode("latin-1").upper()
                self.biffed[(name, EXT[rtype])] = loc
        self.biff_cache = {}

    def names(self, ext):
        return sorted({n for (n, e) in self.override if e == ext} | {n for (n, e) in self.biffed if e == ext})

    def get(self, name, ext):
        name = name.upper()
        if (name, ext) in self.override:
            with open(self.override[(name, ext)], "rb") as f:
                return f.read()
        loc = self.biffed.get((name, ext))
        if loc is None:
            return None
        data, table = self.biff(loc >> 20)
        offset, size = table[loc & 0x3FFF]
        return data[offset:offset + size]

    def biff(self, index):
        if index not in self.biff_cache:
            path = os.path.join(self.game, self.bifs[index])
            if not os.path.exists(path):
                folder, base = os.path.split(path)
                path = next(os.path.join(folder, n) for n in os.listdir(folder) if n.lower() == base.lower())
            with open(path, "rb") as f:
                data = f.read()
            count, _, offset = struct.unpack_from("<3I", data, 8)
            table = {}
            for i in range(count):
                loc, doff, size, _ = struct.unpack_from("<IIIH", data, offset + 16 * i)
                table[loc & 0x3FFF] = (doff, size)
            self.biff_cache[index] = (data, table)
        return self.biff_cache[index]


def slot(data, offset):
    name = data[offset:offset + 8].split(b"\0")[0].decode("latin-1").upper()
    return "" if name == "NONE" else name


def resref(data, offset):
    return data[offset:offset + 8].split(b"\0")[0].decode("latin-1").upper()


def are_actors(data):
    """ARE V1.0 actors by upper-cased name: creature and the placement's scripts."""
    out = {}
    if not data:
        return out
    offset, = struct.unpack_from("<I", data, 0x54)
    count, = struct.unpack_from("<H", data, 0x58)
    for i in range(count):
        a = offset + 0x110 * i
        name = data[a:a + 32].split(b"\0")[0].decode("latin-1").upper()
        scripts = {k: slot(data, a + o) for k, o in (("override", 0x50), ("general", 0x58), ("class", 0x60),
                                                    ("race", 0x68), ("default", 0x70), ("specifics", 0x78))}
        out.setdefault(name, {"cre": resref(data, a + 0x80), "scripts": scripts})
    return out


def cre_items(data):
    offset, count = struct.unpack_from("<II", data, 0x2BC)
    return [resref(data, offset + 0x14 * i) for i in range(count)]


def cre_effects(data):
    """(opcode, parameter1, parameter2, resource) of a creature's own effects."""
    offset, count = struct.unpack_from("<II", data, 0x2C4)
    out = []
    for i in range(count):
        if data[0x33] == 1:
            o = offset + 0x108 * i
            op, _, _, p1, p2 = struct.unpack_from("<IIIii", data, o + 0x8)
            out.append((op, p1, p2, resref(data, o + 0x28)))
        else:
            o = offset + 0x30 * i
            op, = struct.unpack_from("<H", data, o)
            p1, p2 = struct.unpack_from("<ii", data, o + 0x4)
            out.append((op, p1, p2, resref(data, o + 0x14)))
    return out


def itm_equipped(data):
    """(opcode, parameter1, parameter2, resource) of an item's equipped effects."""
    offset, = struct.unpack_from("<I", data, 0x6A)
    first, count = struct.unpack_from("<HH", data, 0x6E)
    out = []
    for i in range(count):
        o = offset + 0x30 * (first + i)
        op, = struct.unpack_from("<H", data, o)
        p1, p2 = struct.unpack_from("<ii", data, o + 0x4)
        out.append((op, p1, p2, resref(data, o + 0x14)))
    return out


def spl_ability_effects(data):
    ab_off, = struct.unpack_from("<I", data, 0x64)
    ab_count, = struct.unpack_from("<H", data, 0x68)
    fx_off, = struct.unpack_from("<I", data, 0x6A)
    out = []
    for a in range(ab_count):
        count, first = struct.unpack_from("<HH", data, ab_off + 0x28 * a + 0x1E)
        for i in range(count):
            o = fx_off + 0x30 * (first + i)
            op, = struct.unpack_from("<H", data, o)
            p1, p2 = struct.unpack_from("<ii", data, o + 0x4)
            out.append((op, p1, p2, resref(data, o + 0x14)))
    return out


def ids_numbers(data):
    """SYMBOL -> number of an IDS file (decimal or 0x numbers)."""
    out = {}
    for line in (data or b"").decode("latin-1").splitlines():
        parts = line.split()
        if len(parts) >= 2:
            try:
                out[parts[1].upper()] = int(parts[0], 0)
            except ValueError:
                pass
    return out


def takes_hit_points(effects, limit):
    """Effects that take hit points to the bottom in one go, as component 300 counts
    them: opcode 12 set to <= limit or <= 10 %, or reduce by >= 90 %; opcode 17 set
    to <= limit or <= 10 %; opcode 18 (modes 1/2, or 4/5 without current hit points)
    the same."""
    for op, p1, p2, _ in effects:
        mode = p2 & 0xFFFF
        if op == 12 and ((mode == 1 and p1 <= limit) or (mode == 2 and p1 <= 10) or (mode == 3 and p1 >= 90)):
            return True
        if op == 17 and ((mode == 1 and p1 <= limit) or (mode == 2 and p1 <= 10)):
            return True
        if op == 18 and ((mode in (1, 4) and p1 <= limit) or (mode in (2, 5) and p1 <= 10)):
            return True
    return False


def forced_spells(script):
    """(target object fields, spell number) of every ForceSpell (113) and
    ReallyForceSpell (181) in a compiled, lower-cased script."""
    return [(target.split(), int(number)) for _, target, number in
            re.findall(rb"ac\n(113|181)ob\n.*?ob\nob\n(.*?)ob\nob\n.*?ob\n(-?\d+) ", script, re.S)]


def is_myself(fields):
    """Object fields of Myself: identifier 1 (the eighth number), all else 0."""
    return len(fields) >= 8 and fields[7] == b"1" and not any(int(x) for x in fields[:7])


def spell_resref(number):
    """SPELL.IDS number to resref: 1xxx SPPR, 2xxx SPWI, 3xxx SPIN, 4xxx SPCL."""
    kind, index = divmod(number, 1000)
    prefix = {1: "SPPR", 2: "SPWI", 3: "SPIN", 4: "SPCL"}.get(kind)
    return "%s%03d" % (prefix, index) if prefix else ""


def cre_priest_spells(data):
    info_off, info_cnt, mem_off, _ = struct.unpack_from("<IIII", data, 0x2A8)
    spells = []
    for i in range(info_cnt):
        level, _, _, kind, first, count = struct.unpack_from("<HHHHII", data, info_off + 16 * i)
        if kind == PRIEST_TYPE:
            for j in range(count):
                o = mem_off + 12 * (first + j)
                spells.append((level, data[o:o + 8].split(b"\0")[0].decode("latin-1").upper()))
    return sorted(spells)


class Checker:
    def __init__(self, res):
        self.res = res
        self.failed = 0
        self.text = {}

    def script(self, name):
        if name not in self.text:
            self.text[name] = (self.res.get(name, "BCS") or b"").lower() if name else b""
        return self.text[name]

    def is_caster(self, name):
        return b"instantprep" in self.script(name)

    def is_melee(self, name):
        # SCS's melee AI, or the base game's melee scripts this mod repairs
        data = self.script(name)
        return name in ("GNMMGSGH", "GNTRPM1") or (b"dmww_genai_difficulty" in data and b"instantprep" not in data)

    def check(self, ok, text):
        print(("PASS  " if ok else "FAIL  ") + text)
        if not ok:
            self.failed += 1

    def melee_before_caster(self, scripts):
        """scripts by run order; returns the melee scripts that run before the first caster AI."""
        for i, name in enumerate(scripts):
            if name and self.is_caster(name):
                return [s for s in scripts[:i] if s and self.is_melee(s)]
        return []


def main():
    res = Resources(sys.argv[1])
    c = Checker(res)
    cres = {n: res.get(n, "CRE") for n in res.names("CRE")}
    cres = {n: d for n, d in cres.items() if d and d[:8] == b"CRE V1.0" and len(d) >= 0x2D4}

    # 100: Shadowed Elven Clerics
    pointing = [n for n, d in cres.items() if "SDELFCS1" in [slot(d, o) for o in CRE_SLOTS if o]]
    c.check(not pointing, "no creature points at the missing SDELFCS1 (%s)" % (", ".join(pointing) or "none"))
    ch1, ch2 = cres.get("SDELFCH1"), cres.get("SDELFCH2")
    if ch1 and ch2:
        casters = [s for s in (slot(ch2, o) for o in CRE_SLOTS if o) if s and c.is_caster(s)]
        c.check(bool(casters), "SDELFCH2 runs an SCS caster script (%s)" % ", ".join(casters))
        c.check(cre_priest_spells(ch2) == cre_priest_spells(ch1), "SDELFCH2 has SDELFCH1's SCS spell selection")

    # 100: no melee AI runs before an SCS caster AI, in creature files and area placements
    bad = []
    for n, d in cres.items():
        found = c.melee_before_caster([slot(d, o) if o else "" for o in CRE_SLOTS])
        if found:
            bad.append("%s: %s" % (n, ", ".join(found)))
    for area in res.names("ARE"):
        d = res.get(area, "ARE")
        if not d or d[:8] != b"AREAV1.0":
            continue
        off, = struct.unpack_from("<I", d, 0x54)
        count, = struct.unpack_from("<H", d, 0x58)
        for i in range(count):
            a = off + 0x110 * i
            flags, = struct.unpack_from("<I", d, a + 0x28)
            emb_off, emb_size = struct.unpack_from("<II", d, a + 0x88)
            cre = d if (not flags & 1 and emb_size >= 0x2D4 and emb_off) else cres.get(slot(d, a + 0x80))
            base = emb_off if cre is d else 0
            scripts = []
            for are_o, cre_o in zip(ARE_SLOTS, CRE_SLOTS):
                own = slot(d, a + are_o)
                scripts.append(own or (slot(cre, base + cre_o) if (cre is not None and cre_o) else ""))
            found = c.melee_before_caster(scripts)
            if found:
                name = d[a:a + 32].split(b"\0")[0].decode("latin-1")
                bad.append("%s %s: %s" % (area, name, ", ".join(found)))
    c.check(not bad, "no melee AI runs before an SCS caster AI (%s)" % ("; ".join(bad) or "none"))
    c.check(res.get("CIETMWK", "BCS") is not None, "CIETMWK.BCS installed")

    # 200: priest preparation
    prepared = [n for n in res.names("BCS") if b"cie_self" in c.script(n)]
    scs_prepared = [n for n in prepared if c.is_caster(n)]
    c.check(len(scs_prepared) > 0, "%d SCS caster scripts carry the preparation" % len(scs_prepared))
    for script in ("SHELFPS1", "CAJSHA1M"):
        c.check(b"cie_self" in c.script(script), "%s carries the preparation" % script)
    # one copy of the blocks names CIE_SELF eight times (four checks, four sets)
    twice = [n for n in prepared if c.script(n).count(b"cie_self") != 8]
    c.check(not twice, "every prepared script has the blocks once (%s)" % (", ".join(twice) or "ok"))

    # 300: Belhifet's final fight (only when installed: it brings CIEBHP3)
    bel = cres.get("BELHIF")
    if bel and res.get("CIEBHP3", "SPL") is not None:
        equipped = []
        for item in cre_items(bel):
            data = res.get(item, "ITM")
            equipped += itm_equipped(data) if data else []
        own = cre_effects(bel)
        c.check(not [e for e in equipped + own if e[0] == 102], "Belhifet has no spell-level immunity")
        c.check(not [e for e in equipped + own if e[0] == 120 and e[2] == 0 and e[1] >= 2],
                "no item or effect of Belhifet stops +2 weapons")
        # his protections come from CIEBELPR, which his script applies
        pr = res.get("CIEBELPR", "SPL")
        pr_fx = spl_ability_effects(pr) if pr else []
        blocked = sorted({e[2] for e in pr_fx if e[0] == 101})
        missing = [op for op in BELHIFET_BLOCKED if op not in blocked]
        c.check(pr is not None and not missing,
                "CIEBELPR protects from opcodes %s (missing: %s)" % (BELHIFET_BLOCKED, missing or "none"))
        protected = {e[3] for e in pr_fx if e[0] == 206}
        limit = max(10, struct.unpack_from("<H", bel, 0x26)[0] // 10)
        setters = []
        for name in res.names("SPL"):
            data = res.get(name, "SPL")
            try:
                if data[:8] == b"SPL V1  " and takes_hit_points(spl_ability_effects(data), limit):
                    setters.append(name)
            except struct.error:
                continue
        unprotected = [s for s in setters if s not in protected]
        c.check(setters and not unprotected, "CIEBELPR protects from the %d spells that set hit points to the bottom "
                "(unprotected: %s)" % (len(setters), ", ".join(unprotected) or "none"))
        c.check(any(e[0] == 321 and e[3] == "CIEBELPR" for e in spl_ability_effects(res.get("CIEBELEN", "SPL") or b"")),
                "CIEBELEN takes CIEBELPR away")
        c.check(any(e[0] == 208 for e in equipped), "Belhifet keeps his minimum hit point")
        first = next((s for s in (slot(bel, o) for o in CRE_SLOTS if o) if s), "")
        c.check(c.script(first).count(b"cie_bel_hp") == 8 and c.script(first).count(b"cie_bel_prep") == 2
                and c.script(first).count(b'cie_bel_pr"') == 2,
                "%s carries the protection, hit point and preparation blocks once" % first)
        # every script that casts the death animation on him drops CIEBELPR first
        death = ids_numbers(res.get("SPELL", "IDS")).get("INNATE_BELHIFETS_DEATH_ANIMATION")
        c.check(death is not None, "SPELL.IDS has INNATE_BELHIFETS_DEATH_ANIMATION")
        enders, unguarded = [], []
        for name in res.names("BCS"):
            script = (res.get(name, "BCS") or b"").lower()
            casts = [1 for fields, number in forced_spells(script) if number == death and is_myself(fields)]
            if casts:
                enders.append(name)
                if script.count(b'"ciebelen"') < len(casts):
                    unguarded.append(name)
        c.check(enders and not unguarded, "the death animation comes after CIEBELEN in %s (missing in: %s)"
                % (", ".join(enders) or "no script", ", ".join(unguarded) or "none"))
        # compiled actions keep a timer as "LOCALS<name>", the timer triggers as
        # "<name>"; a timer set as <name>_timer next to a check of <name> is SCS's
        # broken teleport pause
        text = c.script(first)
        broken = [n for n in re.findall(rb'"locals([^"]+)_timer"', text)
                  if b'"' + n + b'"' in text or b'"locals' + n + b'"' in text]
        c.check(not broken, "%s sets the timers it checks (%s)" % (first, b", ".join(broken).decode() or "ok"))
        for spell in ("CIEBHP3", "CIEBHP4", "CIEBHP5"):
            fx = spl_ability_effects(res.get(spell, "SPL"))
            c.check(len(fx) == 1 and fx[0][0] == 18 and fx[0][2] == 0 and fx[0][1] > 0,
                    "%s raises hit points (%s)" % (spell, fx))
        area = res.get("AR1105", "ARE")
        area_script = slot(area, 0x94) if area else ""
        text = c.script(area_script)
        stage = text.count(b"cie_bel_stage")
        c.check(stage in (6, 8), "%s carries the second wave once (%d stage references)" % (area_script, stage))
        # each cornugon that comes back: the original leaves on entry (DestroySelf on
        # its script name), a copy with the same script name, the placement's
        # scripts and no permanent invisibility comes with the Gate visual
        destroy = [n for s, n in ids_numbers(res.get("ACTION", "IDS")).items() if s.upper().startswith("DESTROYSELF(")]
        placements = are_actors(area)
        back = 0
        for n in (1, 2):
            copy = "CIEBELC%d" % n
            if b'"' + copy.lower().encode() + b'"' not in text:
                continue  # its creature could not be copied: it fights from the start (the installer warns)
            back += 1
            name = "CORNUGON_%d" % n
            cre = res.get(copy, "CRE")
            c.check(cre is not None and cre[0x280:0x2A0].split(b"\0")[0].upper() == name.encode(),
                    "%s keeps the script name %s" % (copy, name))
            c.check(cre is not None and not [e for e in cre_effects(cre) if e[0] == 20], "%s arrives visible" % copy)
            placed = placements.get(name)
            if cre is not None and placed:
                own = {k: slot(cre, o) for k, o in (("override", 0x248), ("class", 0x250), ("race", 0x258),
                                                    ("general", 0x260), ("default", 0x268))}
                c.check(all(own[k] == v for k, v in placed["scripts"].items() if v and k in own),
                        "%s runs its placement's scripts (%s)" % (copy, placed["scripts"]))
            c.check(any(re.search(rb'ac\n%dob\n[^\n]*"%s"ob' % (d, name.lower().encode()), text) for d in destroy),
                    "%s leaves when the party enters" % name)
        c.check(back > 0, "%s brings %d cornugon(s) back" % (area_script, back))
        c.check(b'"spsumgte"' in text, "they come back with the Gate visual")
        if stage == 8:
            third = res.get("CIEBELC3", "CRE")
            c.check(third is not None and third[0x280:0x280 + 14] == b"CIE_CORNUGON_3",
                    "CIEBELC3 has the script name CIE_CORNUGON_3")
            c.check(third is not None and not [e for e in cre_effects(third) if e[0] == 20], "CIEBELC3 arrives visible")
            c.check(b"cie_cornugon_3" in c.script("EEBELKIL"), "EEBELKIL kills the third cornugon")
        spell = res.get("SPIN183", "SPL")
        if spell is not None and any(e[0] == 151 and e[3] == "BELHIF" for e in spl_ability_effects(spell)):
            c.check(not [e for e in spl_ability_effects(spell) if e[0] == 58], "Poquelin's transformation does not dispel")
        # ForceSpell (113) and ReallyForceSpell (181) in the transformation cutscene:
        # none casts a dispelling spell on anyone but Poquelin himself (first object
        # parameter: identifier 1 = Myself)
        dispels = []
        for fields, number in forced_spells(c.script("EEPOQCNG")):
            if is_myself(fields):
                continue
            name = spell_resref(number)
            data = res.get(name, "SPL") if name else None
            if data and any(e[0] == 58 for e in spl_ability_effects(data)):
                dispels.append(name)
        c.check(not dispels, "the transformation cutscene forces no dispel on the party (%s)" % (", ".join(dispels) or "ok"))

    print("%d check(s) failed" % c.failed if c.failed else "all checks passed")
    return 1 if c.failed else 0


if __name__ == "__main__":
    sys.exit(main())
