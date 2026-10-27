"""Check what chriz-iwd-encounters changed in an installed IWD:EE game (read-only).

Usage: python -I tests/check_install.py <game_dir>

Reads the game's resources (override first, then the BIFF files chitin.key lists).
Prints one line per check and exits 1 if any check fails.
"""
import os
import struct
import sys

PRIEST_TYPE = 0
CRE_TYPE, ARE_TYPE, BCS_TYPE = 0x3F1, 0x3F2, 0x3EF
EXT = {CRE_TYPE: "CRE", ARE_TYPE: "ARE", BCS_TYPE: "BCS"}
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

    print("%d check(s) failed" % c.failed if c.failed else "all checks passed")
    return 1 if c.failed else 0


if __name__ == "__main__":
    sys.exit(main())
