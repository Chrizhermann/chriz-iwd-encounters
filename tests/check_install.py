"""Check what chriz-iwd-encounters changed in an installed IWD:EE game (read-only).

Usage: python -I tests/check_install.py <game_dir>

Reads the game's resources (override first, then the BIFF files chitin.key lists).
Prints one line per check and exits 1 if any check fails.
"""
import os
import re
import struct
import sys
from pathlib import Path

PRIEST_TYPE = 0
CRE_TYPE, ARE_TYPE, BCS_TYPE, ITM_TYPE, SPL_TYPE, IDS_TYPE = 0x3F1, 0x3F2, 0x3EF, 0x3ED, 0x3EE, 0x3F0
EXT = {CRE_TYPE: "CRE", ARE_TYPE: "ARE", BCS_TYPE: "BCS", ITM_TYPE: "ITM", SPL_TYPE: "SPL", IDS_TYPE: "IDS"}
# 300: what Belhifet must be protected from (opcode 101 targets): instant death,
# removal from the fight, paralysis and hold
BELHIFET_BLOCKED = (13, 55, 134, 135, 209, 211, 213, 238, 109, 175, 185)
# ... and, as the game's own hold-immune creatures (the golems), the hold texts
# ("Held", "Paralyzed", "Held") and animations
BELHIFET_HOLD_STRINGS = (14102, 35542, 35606)
BELHIFET_HOLD_ANIMATIONS = ("PARALH", "SPFLAYER", "SPMINDAT")
# script slots by run order (SCRLEV.IDS): override, specifics, class, race, general, default
ARE_SLOTS = (0x50, 0x78, 0x60, 0x68, 0x58, 0x70)
CRE_SLOTS = (0x248, None, 0x250, 0x258, 0x260, 0x268)
# 110: OBJECT.IDS Player1-6 and Player1Fill-6Fill, TRIGGER.IDS, STATE.IDS (as a signed 32-bit value)
PARTY_SLOTS = set(range(21, 27)) | set(range(70, 76))
STATECHECK, NEXTTRIGGEROBJECT, INMYAREA, OR_TRIGGER = 0x4037, 0x40E0, 0x40CB, 0x4089
CD_STATE_NOTVALID = 0x80101FEF - 0x100000000


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
        return self.original(name, ext)

    def original(self, name, ext):
        """The BIFF copy, as the game ships it (override/ ignored)."""
        loc = self.biffed.get((name.upper(), ext))
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


def apr_halves(value):
    """Attacks per round in half attacks: 0-5 whole attacks, 6-10 = 1/2, 3/2, 5/2, 7/2, 9/2."""
    return value * 2 if value <= 5 else (value - 6) * 2 + 1


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


def spl_effect_rows(data):
    """Every ability effect of a spell with the fields the checks need."""
    if len(data) < 0x72:
        return []
    ab_off, = struct.unpack_from("<I", data, 0x64)
    ab_count, = struct.unpack_from("<H", data, 0x68)
    fx_off, = struct.unpack_from("<I", data, 0x6A)
    rows = []
    for a in range(ab_count):
        count, first = struct.unpack_from("<HH", data, ab_off + 0x28 * a + 0x1E)
        for i in range(count):
            o = fx_off + 0x30 * (first + i)
            op, _, power = struct.unpack_from("<HBB", data, o)
            p1, p2 = struct.unpack_from("<ii", data, o + 0x4)
            duration, = struct.unpack_from("<I", data, o + 0xE)
            rows.append({"opcode": op, "power": power, "p1": p1, "p2": p2, "timing": data[o + 0xC],
                         "dispel": data[o + 0xD], "duration": duration, "resource": resref(data, o + 0x14)})
    return rows


def multiplies_hit_points(effects):
    """Effects that raise maximum hit points by a percentage (opcode 18, modes 2 and 5,
    more than 100), such as SCS's fiend "staying power"."""
    return any(op == 18 and (p2 & 0xFFFF) in (2, 5) and p1 > 100 for op, p1, p2, _ in effects)


def forced_spells(script):
    """(target object fields, spell number) of every ForceSpell (113) and
    ReallyForceSpell (181) in a compiled, lower-cased script."""
    return [(target.split(), int(number)) for _, target, number in
            re.findall(rb"ac\n(113|181)ob\n.*?ob\nob\n(.*?)ob\nob\n.*?ob\n(-?\d+) ", script, re.S)]


def response_actions(script):
    """(response number, action id, action text) of every action of a compiled,
    lower-cased script, in order."""
    out = []
    for number, response in enumerate(script.split(b"re\n")):
        heads = [(m.start(), int(m.group(1))) for m in re.finditer(rb"ac\n(\d+)ob\n", response)]
        for k, (start, ident) in enumerate(heads):
            end = heads[k + 1][0] if k + 1 < len(heads) else len(response)
            out.append((number, ident, response[start:end]))
    return out


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


def banter_pairs(data):
    """Interact between party slots in a compiled script: (every pair, those without the
    checks of component 110). A pair needs its block to have one response and both
    partners checked outside any OR: alive and able to talk, and one in the other's area."""
    pairs, unchecked = [], []
    text = data.decode("latin-1").replace("\r\n", "\n")
    for block in text.split("CR\nCO\n")[1:]:
        condition, _, body = block.partition("CO\nRS\n")
        triggers, left = [], 0
        for found in re.findall(r'TR\n(\d+) (-?\d+) (\d+) [^\n]*OB\n([^\n]*)OB\nTR', condition):
            if int(found[0]) == OR_TRIGGER:
                left = int(found[1])
            elif left:
                left -= int(found[0]) != NEXTTRIGGEROBJECT
            else:
                triggers.append(found)
        responses = re.findall(r"RE\n(\d+)AC", body)
        for actor, target in re.findall(r"\n168OB\n([^\n]*)OB\nOB\n([^\n]*)OB\n", body):
            actor, target = int(actor.split()[7]), int(target.split()[7])
            if not {actor, target} <= PARTY_SLOTS:
                continue
            pairs.append((actor, target))
            alive = {int(o.split()[7]) for t, value, negated, o in triggers
                     if int(t) == STATECHECK and int(value) == CD_STATE_NOTVALID and int(negated)}
            area = {(int(a[3].split()[7]), int(b[3].split()[7])) for a, b in zip(triggers, triggers[1:])
                    if int(a[0]) == NEXTTRIGGEROBJECT and int(b[0]) == INMYAREA and not int(b[2])}
            if (len([r for r in responses if int(r)]) != 1 or not {actor, target} <= alive
                    or not {(actor, target), (target, actor)} & area):
                unchecked.append((actor, target))
    return pairs, unchecked


def installed_components(game):
    """Component numbers of this mod that the game's WeiDU.log lists, or None without a log."""
    log = Path(game) / "WeiDU.log"
    if not log.exists():
        return None
    found = set()
    for line in log.read_text(encoding="latin-1").splitlines():
        if line.lstrip().startswith("//"):
            continue
        m = re.match(r"\s*~?[^~]*SETUP-CHRIZ-IWD-ENCOUNTERS\.TP2~?\s+#\d+\s+#(\d+)", line, re.I)
        if m:
            found.add(int(m.group(1)))
    return found


def main():
    res = Resources(sys.argv[1])
    c = Checker(res)
    cres = {n: res.get(n, "CRE") for n in res.names("CRE")}
    cres = {n: d for n, d in cres.items() if d and d[:8] == b"CRE V1.0" and len(d) >= 0x2D4}
    installed = installed_components(sys.argv[1])

    def expect(component, detected):
        """Whether to check a component: by WeiDU.log when the game has one (a component
        it lists whose changes are missing fails), else by the component's own marker."""
        if installed is None:
            return detected
        if component in installed and not detected:
            c.check(False, "component %d is in WeiDU.log, but its changes are missing" % component)
            return False
        if component not in installed and detected:
            c.check(False, "component %d is not in WeiDU.log, but its changes are there" % component)
            return False
        return component in installed

    # 100: Shadowed Elven Clerics
    pointing = [n for n, d in cres.items() if "SDELFCS1" in [slot(d, o) for o in CRE_SLOTS if o]]
    c.check(not pointing, "no creature points at the missing SDELFCS1 (%s)" % (", ".join(pointing) or "none"))
    ch1, ch2 = cres.get("SDELFCH1"), cres.get("SDELFCH2")
    if ch1 and ch2:
        casters = [s for s in (slot(ch2, o) for o in CRE_SLOTS if o) if s and c.is_caster(s)]
        donor_has_scs = any(c.is_caster(slot(ch1,o)) for o in CRE_SLOTS if o and slot(ch1,o))
        c.check(bool(casters) if donor_has_scs else "SHELFCS1" in [slot(ch2,o) for o in CRE_SLOTS if o],
                "SDELFCH2 runs the donor caster AI (SCS or SHELFCS1)")
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

    # 110: banter between party slots checks both partners (a game without that banter
    # has nothing to check)
    pairs, unchecked = banter_pairs(res.get("BALDUR", "BCS") or b"")
    if pairs and expect(110, not unchecked):
        c.check(True, "every banter pair in baldur.bcs checks both partners (%d)" % len(pairs))

    # 200: priest preparation
    prepared = [n for n in res.names("BCS") if b"cie_self" in c.script(n)]
    scs_prepared = [n for n in prepared if c.is_caster(n)]
    priest_casters = {slot(d,o) for d in cres.values() for o in CRE_SLOTS if o
                      and d[0x273] in (3,8,11,14,15,16,17,18,21) and c.is_caster(slot(d,o))}
    c.check(priest_casters <= set(scs_prepared), "every existing SCS priest caster carries preparation (%d)" % len(scs_prepared))
    for script in ("SHELFPS1", "CAJSHA1M"):
        c.check(b"cie_self" in c.script(script), "%s carries the preparation" % script)
    # one copy of the blocks names CIE_SELF eight times (four checks, four sets)
    twice = [n for n in prepared if c.script(n).count(b"cie_self") != 8]
    c.check(not twice, "every prepared script has the blocks once (%s)" % (", ".join(twice) or "ok"))

    # 300: Belhifet's final fight (only when installed: it brings CIEBHP3)
    bel = cres.get("BELHIF")
    if expect(300, bool(bel) and res.get("CIEBHP3", "SPL") is not None):
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
        strings = {e[1] for e in pr_fx if e[0] == 267}
        animations = {e[3] for e in pr_fx if e[0] == 296}
        missing = sorted(set(BELHIFET_HOLD_STRINGS) - strings) + sorted(set(BELHIFET_HOLD_ANIMATIONS) - animations)
        c.check(not missing, "CIEBELPR hides the hold texts %s and animations %s (missing: %s)"
                % (BELHIFET_HOLD_STRINGS, BELHIFET_HOLD_ANIMATIONS, missing or "none"))
        # the same as the golems' hold immunity as the game ships it (texts and
        # animations the data marks with a hold or paralysis opcode)
        golem = []
        for item in ("IRONGOL", "GOLSTONE", "GOLCLA"):
            data = res.original(item, "ITM")
            golem += itm_equipped(data) if data else []
        golem_hold = {("267", e[1]) for e in golem if e[0] == 267 and e[2] in (109, 175, 185)} \
            | {("296", e[3]) for e in golem if e[0] == 296 and e[2] in (109, 175, 185)}
        ours = {("267", s) for s in strings} | {("296", a) for a in animations}
        c.check(not golem_hold - ours, "CIEBELPR hides every hold text and animation the base game's golems hide "
                "(%d; missing: %s)" % (len(golem_hold), sorted(golem_hold - ours) or "none"))
        hold_state = ids_numbers(res.get("SPLSTATE", "IDS")).get("HOLD_IMMUNITY")
        c.check(hold_state is None or any(e[0] == 328 and e[2] == hold_state for e in pr_fx),
                "CIEBELPR sets the hold-immune spell state where SPLSTATE.IDS has one (%s)" % hold_state)
        c.check(bel[0x59] == 100 and bel[0x5E] == 100,
                "Belhifet is immune to fire and magic fire (%d, %d)" % (bel[0x59], bel[0x5E]))
        protected = {e[3] for e in pr_fx if e[0] == 206}
        # immune to spell levels 1-3 only (Christopher, 2026-10-29), with the
        # protections from single spells of those levels that his items had
        levels = sorted(e[1] for e in pr_fx if e[0] == 102)
        c.check(levels == [1, 2, 3], "CIEBELPR grants immunity to spell levels 1-3 only (%s)" % levels)
        low = set()
        for item in cre_items(res.original("BELHIF", "CRE") or bel):
            data = res.original(item, "ITM")
            for e in itm_equipped(data) if data else []:
                spell = res.get(e[3], "SPL") if e[0] == 206 and re.match(r"SP(PR|WI)[1-3]\d\d$", e[3]) else None
                if spell and len(spell) >= 0x38 and struct.unpack_from("<H", spell, 0x1C)[0] in (1, 2) \
                        and 1 <= struct.unpack_from("<I", spell, 0x34)[0] <= 3:
                    low.add(e[3])
        lost = sorted(low - protected)
        c.check(not lost, "CIEBELPR keeps his items' %d protections from spells of levels 1-3 (lost: %s)"
                % (len(low), ", ".join(lost) or "none"))
        limit = max(10, struct.unpack_from("<H", bel, 0x26)[0] // 10)
        setters, raisers = [], []
        for name in res.names("SPL"):
            data = res.get(name, "SPL")
            try:
                if data[:8] != b"SPL V1  ":
                    continue
                fx = spl_ability_effects(data)
            except struct.error:
                continue
            if takes_hit_points(fx, limit):
                setters.append(name)
            if multiplies_hit_points(fx):
                raisers.append(name)
        unprotected = [s for s in setters if s not in protected]
        c.check(setters and not unprotected, "CIEBELPR protects from the %d spells that set hit points to the bottom "
                "(unprotected: %s)" % (len(setters), ", ".join(unprotected) or "none"))
        # his hit points are final values, also with SCS (Christopher, 2026-11-03)
        unprotected = [s for s in raisers if s not in protected]
        c.check(not unprotected, "CIEBELPR protects from the %d spells that raise maximum hit points by a "
                "percentage (unprotected: %s)" % (len(raisers), ", ".join(unprotected) or "none"))
        c.check(any(e[0] == 321 and e[3] == "CIEBELPR" for e in spl_ability_effects(res.get("CIEBELEN", "SPL") or b"")),
                "CIEBELEN takes CIEBELPR away")
        c.check(any(e[0] == 208 for e in equipped), "Belhifet keeps his minimum hit point")
        first = next((s for s in (slot(bel, o) for o in CRE_SLOTS if o) if s), "")
        c.check(c.script(first).count(b"cie_bel_hp") == 8 and c.script(first).count(b"cie_bel_prep") == 2
                and c.script(first).count(b'cie_bel_pr"') == 2 and c.script(first).count(b"cie_bel_haste") == 2,
                "%s carries the protection, hit point, preparation and Haste blocks once" % first)
        # Haste from Core Rules up: 30 seconds on, 12 off (Christopher, 2026-11-03);
        # power 0, so his own spell-level immunity does not stop it
        haste = spl_effect_rows(res.get("CIEBELHA", "SPL") or b"")
        on = [r for r in haste if r["opcode"] == 16 and r["p2"] == 0]
        c.check(len(on) == 1 and on[0]["duration"] == 30 and on[0]["timing"] == 0
                and all(r["power"] == 0 for r in haste),
                "CIEBELHA hastes him for 30 seconds at power 0 (%s)" % on)
        # his script starts it once; the spell casts itself again 42 seconds later
        # (delayed, not dispellable), and the ending stops it
        again = [r for r in haste if r["opcode"] == 146 and r["resource"] == "CIEBELHA"]
        c.check(b'"ciebelha"' in c.script(first) and len(again) == 1 and again[0]["timing"] == 4
                and again[0]["duration"] == 42 and not again[0]["dispel"] & 1,
                "%s starts it, and it casts itself again every 42 seconds (%s)" % (first, again))
        c.check(any(e[0] == 321 and e[3] == "CIEBELHA" for e in spl_ability_effects(res.get("CIEBELEN", "SPL") or b"")),
                "CIEBELEN stops the Haste cycle")
        # every script that casts the death animation on him drops CIEBELPR first
        death = ids_numbers(res.get("SPELL", "IDS")).get("INNATE_BELHIFETS_DEATH_ANIMATION")
        c.check(death is not None, "SPELL.IDS has INNATE_BELHIFETS_DEATH_ANIMATION")
        # in the same response, right before each such cast: ApplySpellRES("CIEBELEN",Myself)
        # then SmallWait (the protections are gone two AI ticks before the animation)
        action_ids = ids_numbers(res.get("ACTION", "IDS"))
        apply_id = next((n for s, n in action_ids.items() if s.startswith("APPLYSPELLRES(")), None)
        wait_id = next((n for s, n in action_ids.items() if s.startswith("SMALLWAIT(")), None)
        enders, unguarded = [], []
        for name in res.names("BCS"):
            script = (res.get(name, "BCS") or b"").lower()
            acts = response_actions(script)
            for i, (response, ident, text) in enumerate(acts):
                if ident not in (113, 181) or not any(n == death and is_myself(f) for f, n in forced_spells(text)):
                    continue
                if name not in enders:
                    enders.append(name)
                guarded = (i >= 2 and acts[i - 1][0] == response and acts[i - 1][1] == wait_id
                           and acts[i - 2][0] == response and acts[i - 2][1] == apply_id
                           and b'"ciebelen"' in acts[i - 2][2])
                if not guarded and name not in unguarded:
                    unguarded.append(name)
        c.check(enders and not unguarded, "the death animation comes right after CIEBELEN and a short wait in %s "
                "(missing in: %s)" % (", ".join(enders) or "no script", ", ".join(unguarded) or "none"))
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
            c.check(cre is not None and cre[0x59] == 100 and cre[0x5E] == 100,
                    "%s is immune to fire and magic fire" % copy)
            placed = placements.get(name)
            original = res.get(placed["cre"], "CRE") if placed else None
            c.check(original is None or (original[0x59] == 100 and original[0x5E] == 100),
                    "%s (%s) is immune to fire and magic fire" % (name, placed["cre"] if placed else "?"))
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
            c.check(third is not None and third[0x59] == 100 and third[0x5E] == 100,
                    "CIEBELC3 is immune to fire and magic fire")
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

    # 310: Yxunomei and her temple (only when installed: it brings CIEYXPUR)
    area = res.get("AR4005", "ARE")
    if expect(310, bool(area) and res.get("CIEYXPUR", "BCS") is not None):
        area_script = slot(area, 0x94)
        text = c.script(area_script)
        blocks = re.findall(rb"cr\n(.*?)cr\n", text, re.S)
        spawns = [b for b in blocks if b'"myarea#spawn_group_0"' in b.split(b"rs\n")[0] and b"ac\n7ob\n" in b]
        c.check(len(spawns) == 1, "%s has one spawn block for the mages (%d)" % (area_script, len(spawns)))
        mages = []
        for block in spawns:
            condition = block.split(b"rs\n")[0]
            c.check(b'"myareayxun_attack"' in condition and b'"myareamap_group_hostile5"' not in condition,
                    "the mages come with YXUN_ATTACK, not with MAP_GROUP_HOSTILE5")
            mages = sorted({s.decode().upper() for s in re.findall(rb'"([^"]{1,8})"', block.split(b"rs\n", 1)[1])
                            if res.get(s.decode(), "CRE") is not None})
        for mage in mages:
            c.check(slot(res.get(mage, "CRE"), 0x248) == "CIEYXPUR", "the mage %s runs CIEYXPUR first" % mage)
        # copies of their own: the base game's YUANMAG also comes in AR4004
        c.check(mages and all(m.startswith("CIEYXM") for m in mages),
                "the spawn block creates its own copies of the mages (%s)" % ", ".join(mages))
        c.check(b'"localscie_yxu_pursue"' in c.script("CIEYXPUR"), "CIEYXPUR walks the mages to the party")
        # the champions jump to her and join her guards' team
        off, = struct.unpack_from("<I", area, 0x54)
        count, = struct.unpack_from("<H", area, 0x58)
        girl, champions, guard_team = None, [], ""
        for i in range(count):
            a = off + 0x110 * i
            name = area[a:a + 32].split(b"\0")[0].decode("latin-1")
            flags, = struct.unpack_from("<I", area, a + 0x28)
            scripts = [slot(area, a + o) for o in ARE_SLOTS]
            if name.upper() == "YXUNOMEI GIRL FORM":
                girl = struct.unpack_from("<HH", area, a + 0x20)
            if resref(area, a + 0x80) in ("YUCHAMP", "CDYUCHAM") and flags & 8:
                champions.append(name.replace(" ", ""))
            if "D5YXNATK" in scripts and not guard_team:
                guard_team = next((s for s in scripts if s.startswith("GNTEAM")), "")
        # "she has appeared" is her script's AREA_VARBit2 (the area script cannot find
        # her by name: Exists("Yxunomei") stays false for the summoned Yxunomei)
        own = [s for s in (slot(cres["TANARRI"], o) for o in CRE_SLOTS if o) if s] if "TANARRI" in cres else []
        if any(b'"myareaarea_varbit2"' in c.script(s) for s in own):
            c.check(text.count(b'"myareaarea_varbit2"') == 3,
                    "the champions and elites wait for her script's AREA_VARBit2 (%d)" % text.count(b'"myareaarea_varbit2"'))
        c.check(len(champions) == 2, "two champions are placed by name (%s)" % ", ".join(champions))
        for name in champions:
            c.check(text.count(b'"' + name.lower().encode() + b'"') >= 5,
                    "%s goes to her side (%d references)" % (name, text.count(b'"' + name.lower().encode() + b'"')))
        c.check(bool(guard_team) and b'"' + guard_team.lower().encode() + b'"' in text,
                "the champions join her guards' team %s" % guard_team)
        # Hard two, Insane three elites
        c.check(text.count(b'"yuaewsw"') == 5 and text.count(b'"myareacie_yxu_elites"') == 6,
                "two elites on Hard and three on Insane (%d creations)" % text.count(b'"yuaewsw"'))
        # the pentagram's traps go off for the party's side only
        entered = next((n for s, n in ids_numbers(res.get("TRIGGER", "IDS")).items() if s.startswith("ENTERED(")), None)
        roff, = struct.unpack_from("<I", area, 0x5C)
        rcount, = struct.unpack_from("<H", area, 0x5A)
        near = []
        for i in range(rcount):
            r = roff + 0xC4 * i
            rtype, x1, y1, x2, y2 = struct.unpack_from("<5H", area, r + 0x20)
            if girl and rtype == 0 and ((x1 + x2) // 2 - girl[0]) ** 2 + ((y1 + y2) // 2 - girl[1]) ** 2 <= 400 ** 2:
                near.append(slot(area, r + 0x7C))
        c.check(len(near) == 3 and all(s.startswith("CIEYXT") for s in near),
                "the 3 pentagram traps run copies (%s)" % ", ".join(near))
        for script in sorted(set(near)):
            eas = [int(ea) for t, ea in re.findall(rb"tr\n(\d+) [^\n]*ob\n(-?\d+) ", c.script(script)) if int(t) == entered]
            c.check(eas and all(ea == 30 for ea in eas), "%s goes off on Entered([GOODCUTOFF]) only (%s)" % (script, eas))
        # no balor telekinesis (SCS installs it only outside IWD:EE)
        if res.get("DW#BATEL", "SPL") is None:
            tanarri = cres.get("TANARRI")
            own = [s for s in (slot(tanarri, o) for o in CRE_SLOTS if o) if s] if tanarri else []
            c.check(own and not [s for s in own if b'"dw#batel"' in c.script(s)],
                    "Yxunomei's scripts do not cast the missing DW#BATEL (%s)" % ", ".join(own))

    # 320: the orog raid on Kuldahar (only when installed: it brings CIEKULMA)
    area = res.get("AR2100", "ARE")
    if expect(320, bool(area) and res.get("CIEKULMA", "BCS") is not None):
        text = c.script(slot(area, 0x94))
        blocks = re.findall(rb"cr\n(.*?)cr\n", text, re.S)
        raid = [b for b in blocks if b'"myarea#spawn_group_1"' in b.split(b"rs\n")[0]]
        spawned = sorted({s.decode().upper() for b in raid for s in re.findall(rb'"([^"]{1,8})"', b.split(b"rs\n", 1)[1])
                          if res.get(s.decode(), "CRE") is not None})
        orogs = {n: cres[n] for n in spawned if n in cres and slot(cres[n], 0x268) == "KUATKORO"}
        top = max(struct.unpack_from("<I", d, 0x14)[0] for d in orogs.values()) if orogs else 0
        leaders = sorted(n for n, d in orogs.items() if struct.unpack_from("<I", d, 0x14)[0] == top)
        c.check(len(orogs) >= 2 and 0 < len(leaders) < len(orogs),
                "the raid has orogs and leaders (%s; leaders %s)" % (", ".join(sorted(orogs)), ", ".join(leaders)))
        for n, d in sorted(orogs.items()):
            hp, = struct.unpack_from("<H", d, 0x26)
            if n in leaders:
                c.check(hp >= 70 and apr_halves(d[0x53]) >= 4 and d[0x52] <= 10 and slot(d, 0x260) == "CIEKULMA",
                        "the leader %s: %d hit points, %d attacks, THAC0 %d, waits for the horn (%s)"
                        % (n, hp, d[0x53], d[0x52], slot(d, 0x260)))
            else:
                c.check(hp >= 45 and slot(d, 0x260) == "CIEKULAV",
                        "the orog %s: %d hit points, wakes with the raid (%s)" % (n, hp, slot(d, 0x260)))
        c.check(b'"myareacie_kul_alert"' in c.script("CIEKULAV") and b'"myareacie_kul_wave"' not in c.script("CIEKULAV")
                and b'"2100_attack"' in c.script("CIEKULAV"),
                "CIEKULAV wakes with the raid and leaves after four days")
        c.check(b'"myareacie_kul_wave"' in c.script("CIEKULMA") and b'"myareacie_kul_alert"' not in c.script("CIEKULMA")
                and b'"2100_attack"' in c.script("CIEKULMA"),
                "CIEKULMA wakes with the horn only and leaves after four days")
        defenders = sorted({slot(cres[n], 0x260) for n in spawned if n in cres and n not in orogs} - {""})
        for script in defenders:
            text_d = c.script(script)
            c.check(b'"myareacie_kul_alert"' not in text_d and b'"myareacie_kul_wave"' not in text_d
                    and text_d.count(b'"2100_attack"') >= 1,
                    "the defenders' %s keeps its wake rule and sends the unwoken away after four days" % script)
        c.check(b'"myareacie_kul_alert"' in c.script("KUATKREM"), "KUATKREM raises the raid's alert")
        attacked = next((n for s, n in ids_numbers(res.get("TRIGGER", "IDS")).items() if s.startswith("ATTACKEDBY(")), None)
        orog_blocks = re.findall(rb"cr\n(.*?)cr\n", c.script("KUATKORO"), re.S)
        back = [b for b in orog_blocks if any(int(t) == attacked and int(ea) == 128 for t, ea in
                                               re.findall(rb"tr\n(\d+) [^\n]*ob\n(-?\d+) ", b.split(b"rs\n")[0]))]
        c.check(len(back) == 1, "KUATKORO fights back against the defenders (%d block)" % len(back))
        c.check(bool(orog_blocks) and b"ac\n22ob\n" in orog_blocks[-1].split(b"rs\n", 1)[1],
                "KUATKORO ends with the walk to the party")
        c.check(text.count(b'"myareacie_kul_wave"') == 4 and b'"s_horn"' in text,
                "the area sounds the war horn for the leaders")
        arundel = [b for b in blocks if b'"globalkuldahar_alarm"' in b.split(b"rs\n")[0] and b"ac\n7ob\n" in b]
        c.check(len(arundel) == 1 and b'"globalsprite_is_deadyxunomei"' in arundel[0].split(b"rs\n")[0],
                "the town alarm's Arundel only comes while Yxunomei lives")

    # 330: Joril's throne room (only when installed: the court's script carries it)
    area = res.get("AR7004", "ARE")
    placed = are_actors(area)
    court = sorted({s for p in placed.values() if p["cre"] in ("JORIL", "GIANTFS", "GIANTFG")
                    for s in p["scripts"].values() if s and s != "EFDELDEF" and not s.startswith("GNTEAM")})
    if expect(330, bool(court) and any(b'"localscie_jor_rage"' in c.script(s) for s in court)):
        joril = cres.get("JORIL")
        c.check(joril is not None and struct.unpack_from("<H", joril, 0x26)[0] == 185,
                "Joril has %d hit points" % (struct.unpack_from("<H", joril, 0x26)[0] if joril else 0))
        for script in court:
            c.check(b'"localscie_jor_hold"' in c.script(script) and b'"localscie_jor_rage"' in c.script(script),
                    "%s casts Hold Person and uses the Berserker rage once" % script)
        text = c.script(slot(area, 0x94))
        gorg = next((p for p in placed.values() if p["cre"] == "GORG"), None)
        gorg_scripts = [s for s in gorg["scripts"].values() if s] if gorg else []
        c.check(any(b'"myareacie_jor_gorg"' in c.script(s) and b'"myareamap_group_hostile1"' in c.script(s)
                    for s in gorg_scripts), "Gorg turns his pack hostile (%s)" % ", ".join(gorg_scripts))
        wolves = [n.replace(" ", "").lower() for n, p in placed.items() if p["cre"] == "WINWOLFP"]
        c.check(wolves and all(b'"' + w.encode() + b'"' in text for w in wolves),
                "the area sends Gorg's %d wolves to him" % len(wolves))
        blocks = re.findall(rb"cr\n(.*?)cr\n", text, re.S)
        badge = [b for b in blocks if b'"globaljoril_badge"' in b.split(b"rs\n")[0]]
        paying = [b for b in badge if b'"level_10_average"' in b.lower()]
        c.check(len(badge) == 2 and len(paying) == 1 and b'"globalgot_joril_badge"' in paying[0].split(b"rs\n")[0],
                "Joril's badge pays only when he did not hand it over (%d blocks, %d paying)" % (len(badge), len(paying)))

    # 340: Maiden Ilmadia's forge (only when installed: her script carries it)
    area = res.get("AR8011", "ARE")
    placed = are_actors(area)
    ilm = placed.get("MAIDEN ILMADIA")
    ilm_scripts = [s for s in ilm["scripts"].values() if s and not s.startswith("GNTEAM")] if ilm else []
    if expect(340, bool(ilm_scripts) and any(b'"localscie_ilm_aura"' in c.script(s) for s in ilm_scripts)):
        cre = cres.get("ILMADIA")
        c.check(cre is not None and struct.unpack_from("<H", cre, 0x26)[0] == 135,
                "Maiden Ilmadia has %d hit points" % (struct.unpack_from("<H", cre, 0x26)[0] if cre else 0))
        for spell in ("SPCL102", "SPCL103", "SPCL423"):
            c.check(any(b'"' + spell.lower().encode() + b'"' in c.script(s) for s in ilm_scripts),
                    "Ilmadia's script uses %s" % spell)
        text = c.script(slot(area, 0x94))
        giants = [n.replace(" ", "").lower() for n, p in placed.items() if p["cre"] in ("GIANTFIR", "GIANTFI2")]
        c.check(giants and b'"myareacie_ilm_rally"' in text and all(b'"' + g.encode() + b'"' in text for g in giants),
                "the area sends her %d fire giants to her side" % len(giants))
        teams = sorted({s for p in placed.values() for s in p["scripts"].values() if s.startswith("GNTEAM")})
        c.check("GNTEAM2M" not in teams, "no placement in the forge runs GNTEAM2M (%s)" % ", ".join(teams))
        typo = [s for p in placed.values() for s in p["scripts"].values() if s and b'"maiden_ilmadia"' in c.script(s)]
        c.check(not typo, "no script in the forge checks the missing name Maiden_Ilmadia (%s)" % (", ".join(sorted(set(typo))) or "none"))
        drow = sorted({s for p in placed.values() if p["cre"] in ("DROWPM", "DW#DRPM2")
                       for s in p["scripts"].values() if s and s != "EFDELDEF" and not s.startswith("GNTEAM")})
        for script in drow:
            c.check(b'"localscie_group"' in c.script(script), "the drow's %s blesses its allies once" % script)

    # 350: the Idol (only when installed: its script carries the cast timer)
    area = res.get("AR8012", "ARE")
    placed = are_actors(area)
    idol = placed.get("THE IDOL")
    idol_script = next((s for s in idol["scripts"].values() if s), "") if idol else ""
    if expect(350, bool(idol_script) and b'"localscie_idol_cast"' in c.script(idol_script)):
        text_i = c.script(idol_script)
        spells = ids_numbers(res.get("SPELL", "IDS"))
        pwk = spells.get("WIZARD_POWER_WORD_KILL")
        c.check(pwk is not None and not [n for _, n in forced_spells(text_i) if n == pwk]
                and b"ac\n113ob\n" in text_i, "the Idol casts without Power Word: Kill")
        cre = cres.get("IDOL")
        c.check(cre is not None and struct.unpack_from("<H", cre, 0x26)[0] == 225 and any(e[0] == 126 for e in cre_effects(cre)),
                "the Idol has %d hit points and does not move" % (struct.unpack_from("<H", cre, 0x26)[0] if cre else 0))
        c.check(b'"myareacie_idol_rally"' in text_i, "the Idol calls its undead when attacked")
        text = c.script(slot(area, 0x94))
        undead = [n.replace(" ", "").lower() for n, p in placed.items() if p["cre"] in ("MUMMYG", "ZOMBIEL")]
        c.check(undead and all(b'"' + u.encode() + b'"' in text for u in undead),
                "the area sends its %d greater mummies and zombie lords to it" % len(undead))
        lords = [n for n, p in placed.items() if p["cre"] == "ZOMBIEL"]
        c.check(lords and all(placed[n]["scripts"]["race"] == "" for n in lords),
                "the zombie lords' own race script (their aura) runs (%d)" % len(lords))
        doff, = struct.unpack_from("<I", area, 0xA8)
        dn, = struct.unpack_from("<I", area, 0xA4)
        badge = [slot(area, doff + 0xC8 * i + 0x80) for i in range(dn) if resref(area, doff + 0xC8 * i + 0x78)]
        c.check(len(badge) == 6 and len(set(badge)) == 6 and all(s.startswith("CIEBDG") for s in badge)
                and all(b'"globalcie_idol_door_' in c.script(s) for s in badge),
                "the six badge doors count once each (%s)" % ", ".join(badge))
        hidden = [slot(area, doff + 0xC8 * i + 0x80) for i in range(dn)
                  if not resref(area, doff + 0xC8 * i + 0x78) and slot(area, doff + 0xC8 * i + 0x80)]
        c.check(hidden and all(b'"globalall_keys"' in c.script(s) for s in hidden),
                "the hidden door checks ALL_KEYS (%s)" % ", ".join(hidden))

    # 360: Poquelin in the Ascension Cave (only when installed: it brings CIEPOQ)
    area = res.get("AR8013", "ARE")
    if expect(360, bool(area) and res.get("CIEPOQ", "CRE") is not None):
        off, = struct.unpack_from("<I", area, 0x54)
        count, = struct.unpack_from("<H", area, 0x58)
        poq = None
        for i in range(count):
            a = off + 0x110 * i
            if resref(area, a + 0x80) == "CIEPOQ":
                poq = (area[a:a + 32].split(b"\0")[0].decode("latin-1").replace(" ", ""),
                       [slot(area, a + o) for o in ARE_SLOTS])
        c.check(poq is not None, "Poquelin's placement in the cave uses CIEPOQ")
        cre = res.get("CIEPOQ", "CRE")
        blocked = sorted({e[2] for e in cre_effects(cre) if e[0] == 101})
        c.check(struct.unpack_from("<H", cre, 0x26)[0] == 420 and all(op in blocked for op in (13, 55, 134, 209, 211, 238)),
                "CIEPOQ has %d hit points and protections %s" % (struct.unpack_from("<H", cre, 0x26)[0], blocked))
        original = res.get("POQUELIN", "CRE")
        c.check(original is not None and not [e for e in cre_effects(original) if e[0] == 101 and e[2] == 238],
                "the finale's Poquelin (POQUELIN.CRE) is unchanged")
        if poq:
            name, scripts = poq
            main = next((s for s in scripts if s), "")
            text_p = c.script(main)
            c.check(b'"localscie_poq_jump"' in text_p and b'"myareacie_poq_wave"' in text_p,
                    "%s jumps once below three quarters and calls the next wave" % main)
            text = c.script(slot(area, 0x94))
            c.check(b'"myareacie_poq_wave"' in text and b'"spawn_timer"' in text, "the area ends the pause before the next wave")
            scenes = sorted({s.decode().upper() for s in re.findall(rb'"([a-z0-9_#]{1,8})"', text_p) if res.get(s.decode(), "BCS")
                             and s.decode().upper().startswith(main[:5]) and s.decode().upper() != main})
            for scene in scenes:
                c.check(b'"poquelin"' not in c.script(scene) and b'"' + name.lower().encode() + b'"' in c.script(scene),
                        "the escape cutscene %s names him %s" % (scene, name))

    # 370: Cryshal-Tirith (only when installed: it brings CIEPOMRC)
    area = res.get("AR1103", "ARE")
    real = cres.get("EEPOMAB")
    if expect(370, bool(area) and bool(real) and res.get("CIEPOMRC", "SPL") is not None):
        name, = struct.unpack_from("<I", real, 0x08)
        images = {n: cres.get("POMIMG%d" % n) for n in range(1, 6)}
        c.check(all(d is not None and struct.unpack_from("<I", d, 0x08)[0] == name for d in images.values()),
                "the five images carry the real Pomab's name (%d)" % name)
        c.check(("OHPOMREV" in [e[3] for e in spl_ability_effects(res.get("CIEPOMRC", "SPL")) if e[0] == 321]),
                "CIEPOMRC lifts OHPOMREV's reveal")
        c.check(res.get("CIEPOMIL", "SPL") is not None and 276 in [e[0] for e in spl_ability_effects(res.get("CIEPOMIL", "SPL"))],
                "CIEPOMIL makes them illusions again")
        text = c.script(slot(area, 0x94))
        blocks = re.findall(rb"cr\n(.*?)cr\n", text, re.S)
        shuffle = [b for b in blocks if b'"myareacie_pom_shuffle"' in b.split(b"rs\n")[0]]
        names = [b'"pomabr"'] + [b'"pomimg%d"' % n for n in range(1, 6)]
        c.check(len(shuffle) == 1 and all(n in shuffle[0] for n in names + [b'"cdhp3000"', b'"ciepomrc"', b'"ciepomil"']),
                "the area heals, re-hides and shuffles Pomab and his images (%d block(s))" % len(shuffle))
        counting = [b for b in blocks if b'"globalsprite_is_deadfake_pomab"' in b.split(b"rs\n", 1)[-1]
                    and b'"myareacie_pom_shuffle"' in b.split(b"rs\n", 1)[-1]]
        c.check(len(counting) >= 5, "each counted hit on Pomab starts the shuffle (%d block(s))" % len(counting))
        mine = [s for s in (slot(real, o) for o in CRE_SLOTS if o) if s]
        c.check(mine and not any(b'"cdhp3000"' in c.script(s) or b'"globalfake_pomab_dead"' in c.script(s) for s in mine),
                "Pomab's own scripts (%s) neither heal him nor read FAKE_POMAB_DEAD" % ", ".join(mine))
        c.check(mine and b'"myareacie_pom_pressed"' in c.script(mine[0]) and c.script(mine[0]).count(b'"localspomab_illusion"') >= 2,
                "Pomab's first script (%s) tells the sentries when he is pressed and can be revealed again" % (mine[0] if mine else "-"))
        firsts = sorted({next((s for s in (slot(d, o) for o in CRE_SLOTS if o) if s), "") for d in images.values() if d})
        c.check(firsts and all(c.script(s).count(b'"localspomab_illusion"') >= 4 for s in firsts),
                "the images' %s can be revealed again after a shuffle" % ", ".join(firsts))
        placed = are_actors(area)
        sentries = [p for p in placed.values() if p["cre"] in ("SENTRY", "CIESENTR")]
        c.check(sentries and all(p["cre"] == "CIESENTR" for p in sentries), "the %d sentries use CIESENTR" % len(sentries))
        cre = res.get("CIESENTR", "CRE")
        c.check(cre is not None and struct.unpack_from("<H", cre, 0x26)[0] == 240,
                "CIESENTR has %d hit points" % (struct.unpack_from("<H", cre, 0x26)[0] if cre else 0))
        for script in sorted({s for p in sentries for s in p["scripts"].values() if s}):
            t = c.script(script)
            sb = re.findall(rb"cr\n(.*?)cr\n", t, re.S)
            # the wake-up block heals with CDHP3000; HPLT is trigger 0x4012 (16402)
            wake = [b for b in sb if b'"localsoh_dead"' in b.split(b"rs\n")[0] and b'"cdhp3000"' in b]
            c.check(b'"myareacie_pom_pressed"' in t and b'"pomabr"' in t, "%s guards Pomab" % script)
            # SetGlobalTimer stores scope and name in one string, the timer triggers two
            c.check(len([b for b in sb if b'"localsoh_dead_timer"' in b.split(b"rs\n", 1)[-1]]) == 2,
                    "%s plays dead for half as long from Core Rules up" % script)
            c.check(len(wake) == 1 and b"tr\n16402 " not in wake[0],
                    "%s: a sentry stands up when its time is up, however many hit points it has" % script)

    # 380: Mebdinga's barrow (only when installed: her wail script has its own timer)
    area = res.get("AR9400", "ARE")
    placed = are_actors(area)
    meb = next((p for p in placed.values() if p["cre"] == "MEBDING"), None)
    meb_scripts = [s for s in meb["scripts"].values() if s] if meb else []
    wail = next((s for s in meb_scripts if b'"localscie_meb_wail"' in c.script(s)), "")
    if expect(380, bool(wail)):
        t = c.script(wail)
        c.check(b'"#localtimer"' not in t, "Mebdinga's %s no longer shares her lines' timer" % wail)
        c.check(b'"localscie_meb_run"' in t, "she runs from an attacker at most every three rounds")
        c.check(b'"localscie_meb_cry"' in t and b'"localscie_meb_surge"' in t,
                "she sends her War Cry and has her Lament below half on Hard and Insane")
        c.check(any(c.script(s).count(b'"globalknow_soul"') >= 2 and b'"minhp1"' in c.script(s) for s in meb_scripts),
                "hostile before the talk she becomes mortal and the party learns of the soul")
        text = c.script(slot(area, 0x94))
        c.check(b'"myareacie_meb_guard"' in text and text.count(b'"mebdinga"') >= 2,
                "the area sends her honour guard to her")
        ini = (res.get("AR9400", "INI") or b"").decode("latin-1")
        gates = {"VIRGIN01": "EFDELINS", "VIRGIN09": "EFDELINS", "VIRGIN15": "EFDELINS", "VIRGIN26": "EFDELINS",
                 "DDEAD18": "EFDELINS", "DDEAD20": "EFDELINS", "BWIGHT25": "EFDELINS", "VIRGIN03": "EFDELEAS",
                 "VIRGIN22": "EFDELEAS", "VIRGIN25": "EFDELEAS", "DDEAD05": "EFDELHRD", "DDEAD08": "EFDELHRD",
                 "BWIGHT12": "EFDELHRD"}
        missing = []
        for section, gate in gates.items():
            m = re.search(r"^\[%s\](.*?)(?=^\[|\Z)" % section, ini, re.S | re.M | re.I)
            if not m:
                continue
            o = re.search(r"^script_override\s*=\s*(\S*)", m.group(1), re.M | re.I)
            script = (o.group(1) if o else "").upper()
            if script != gate and b'"locals%s_inactive"' % gate.lower().encode() not in c.script(script):
                missing.append("%s=%s" % (section, script or "-"))
        c.check(not missing, "the barrow's spawn file runs all its difficulty gates (%s)" % (", ".join(missing) or "ok"))

    # 390: Icasaracht (only when installed: the fallback no longer creates a second gem)
    area = res.get("AR9604", "ARE")
    text = c.script(slot(area, 0x94)) if area else b""
    blocks = re.findall(rb"cr\n(.*?)cr\n", text, re.S)
    fallback = [b for b in blocks if b'"ildrgded"' in b]
    if expect(390, len(fallback) == 2):
        for name, hp in (("ICASA", 650), ("DLSGEM", 250)):
            cre = cres.get(name)
            c.check(cre is not None and struct.unpack_from("<H", cre, 0x26)[0] == hp,
                    "%s has %d hit points" % (name, struct.unpack_from("<H", cre, 0x26)[0] if cre else 0))
        c.check(any(b'"dlsgem"' not in b for b in fallback), "with the gem there, the fallback creates no second gem")
        c.check(b'"ring91"' not in c.script("ILDRGDED"), "the fallback cutscene fills the gem's ring slot")
        first, second = cres.get("SARUNPR"), cres.get("DWSARU0")
        if first and second:
            rnd = {i for i in cre_items(first) if i.startswith("DW#RND")}
            c.check(rnd <= set(cre_items(second)), "DWSARU0 carries SARUNPR's random items (%s)" % ", ".join(sorted(rnd)))
            c.check(first[0x53] == 1 and second[0x53] == 1, "the underpriestesses no longer have five attacks per round")
    # 400: Lord Maluradek (only when installed: his banishing script carries the alarm)
    area = res.get("AR9712", "ARE")
    placed = are_actors(area)
    lord = next((p for p in placed.values() if p["cre"] == "LORDM"), None)
    lord_scripts = [s for s in lord["scripts"].values() if s] if lord else []
    banish = next((s for s in lord_scripts if b'"localscie_mal_alarm"' in c.script(s)), "")
    if expect(400, bool(banish)):
        t = c.script(banish)
        blocks = re.findall(rb"cr\n(.*?)cr\n", t, re.S)
        for room in (b"1", b"2", b"3"):
            flag = b'"myareateleport_' + room + b'"'
            c.check(len([b for b in blocks if flag in b.split(b"rs\n", 1)[-1]]) >= 2,
                    "a banishment to room %s and the alarm below half set TELEPORT_%s" % (room.decode(), room.decode()))
        cre = cres.get("LORDM")
        c.check(cre is not None and struct.unpack_from("<H", cre, 0x26)[0] == 350,
                "Lord Maluradek has %d hit points" % (struct.unpack_from("<H", cre, 0x26)[0] if cre else 0))
        items = cre_items(cre) if cre else []
        so, = struct.unpack_from("<I", cre, 0x2B8) if cre else (0,)
        gloves = struct.unpack_from("<h", cre, so + 6)[0] if cre else -1
        c.check("CIIGEN" not in items or (0 <= gloves < len(items) and items[gloves] == "CIIGEN"),
                "Lord Maluradek wears his immunity gloves (CIIGEN)")
        for plate in ("KEANIMPH", "KEANIMP2"):
            d = cres.get(plate)
            scripts = [slot(d, o) for o in CRE_SLOTS if o] if d else []
            c.check(bool({"DWMESSGE", "EFATKMEL"} & set(scripts)), "%s fights (%s)" % (plate, ", ".join(s for s in scripts if s)))
        holders = [p for p in placed.values() if "KEBEHLDD" in p["scripts"].values() and "KEBEHLD1" in p["scripts"].values()]
        c.check(b"myareadance_cutscene" in c.script("CIEMALBH"), "the first beholder has its dance hold in its override script")
        order = ["override", "specifics", "class", "race", "general", "default"]
        c.check(all(order.index(next(k for k, v in p["scripts"].items() if v == "KEBEHLDD"))
                    < order.index(next(k for k, v in p["scripts"].items() if v == "KEBEHLD1")) for p in holders),
                "the dancing beholder's hold runs before its fight script (%d)" % len(holders))

    # 410: the Luremaster (only when installed: his placement runs CIELURHP)
    area = res.get("AR9711", "ARE")
    lure_scripts = []
    if area:
        # by creature, not by name: the riddle form (GBARD) carries the same name
        off, = struct.unpack_from("<I", area, 0x54)
        count, = struct.unpack_from("<H", area, 0x58)
        for i in range(count):
            a = off + 0x110 * i
            if resref(area, a + 0x80) == "TRGBARD" and not lure_scripts:
                lure_scripts = [s for s in (slot(area, a + o) for o in ARE_SLOTS) if s]
    if expect(410, "CIELURHP" in lure_scripts):
        missing = [s for s in lure_scripts if res.get(s, "BCS") is None]
        c.check(not missing, "every script slot of the Luremaster points at a script (%s)" % (", ".join(missing) or "ok"))
        c.check("DULURWRP" not in lure_scripts, "his old hop circuit no longer runs beside the new hop")
        t = c.script("CIELURHP")
        c.check(b'"cie_lur_hop" "locals"' in t and t.count(b"ac\n") >= 9,
                "he opens with Improved Invisibility and hops away from an enemy next to him")
        spells = next((s for s in lure_scripts if re.search(rb'tr\n.*?"spwi323"',c.script(s),re.S)
                       or re.search(rb"tr\n\d+ 2323 ", c.script(s))), "")
        c.check(bool(spells) and not re.search(rb"tr\n\d+ 2302 ", c.script(spells)),
                "his Dispel Magic entry checks the Dispel Magic he memorises (%s)" % (spells or "-"))
        text = c.script(slot(area, 0x94))
        c.check(b'"cie_lur_heroes"' in text and b'"sprite_is_deadar9711_hero"' in text,
                "each fallen spectral hero brings its replacement")

    print("%d check(s) failed" % c.failed if c.failed else "all checks passed")
    return 1 if c.failed else 0


if __name__ == "__main__":
    sys.exit(main())
