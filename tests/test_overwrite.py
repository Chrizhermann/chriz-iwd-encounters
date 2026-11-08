"""Install into data-only fixtures and check decided output after edited input.

Usage: python -I tests/test_overwrite.py WEIDU REFERENCE [base|edited|embedded|stack]
The reference is read only. No game executable, saves, lab or Docker is used.
"""
import importlib.util
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("overwrite_fixture", ROOT / "tests/overwrite_fixture.py")
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)
check = fixture.check
WEIDU, REFERENCE, SCENARIO = sys.argv[1], Path(sys.argv[2]), sys.argv[3] if len(sys.argv) > 3 else "base"
sys.argv[1:] = []
COMPONENTS = [100, 110, 200, *range(300, 411, 10)]


def word(data, offset):
    return struct.unpack_from("<H", data, offset)[0]


def long(data, offset):
    return struct.unpack_from("<I", data, offset)[0]


def actor_rows(data):
    start = long(data, 0x54)
    return [data[start + i * 0x110:start + (i + 1) * 0x110]
            for i in range(word(data, 0x58))]


def actor_name(row):
    return row[:32].split(b"\0")[0].decode("ascii").upper()


def script_blocks(data):
    return tuple(re.findall(rb"CR\n(.*?)CR\n", data.replace(b"\r\n", b"\n"), re.S))


class Overwrite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = Path(tempfile.mkdtemp(prefix="overwrite-", dir=ROOT))
        cls.game = cls.folder / "fixture"
        fixture.extract(REFERENCE, cls.game, original=SCENARIO != "stack")
        cls.ov = cls.game / "override"
        if SCENARIO == "stack":
            # Undo this mod's previous install using copies of its own backups,
            # leaving the reference and all preceding mods untouched.
            backup = REFERENCE / "weidu_external/backup/chriz-iwd-encounters"
            for component in reversed(COMPONENTS):
                directory = backup / str(component)
                if directory.exists():
                    for source in directory.iterdir():
                        if source.suffix.lower() in {".are", ".cre", ".bcs", ".spl", ".itm", ".ini"}:
                            shutil.copyfile(source, cls.ov / source.name.lower())
        cls.sentinel = b"PRESERVE_UNRELATED"
        if SCENARIO == "edited":
            cls.mutate()
        if SCENARIO == "embedded":
            cls.embed()
        cls.review_fixtures()
        selected = "DWMESSGE" if (cls.ov / "dwmessge.bcs").exists() else "EFATKMEL"
        cls.selected_melee = selected
        melee = script_blocks((cls.ov / (selected.lower() + ".bcs")).read_bytes())
        cls.plate_expected = {}
        for name in ("KEANIMPH", "KEANIMP2"):
            data = (cls.ov / (name.lower() + ".cre")).read_bytes()
            previous = check.slot(data, 0x260)
            prefix = script_blocks((cls.ov / (previous.lower() + ".bcs")).read_bytes()) if previous and previous != selected else ()
            cls.plate_expected[name] = (prefix + melee, data[0x268:0x270])
        cls.validation_failed = False
        cls.results = []
        cls.install()

    @classmethod
    def tearDownClass(cls):
        # Keep a failed fixture for diagnosis. Successful runs leave only this report.
        if not cls.validation_failed and not any("ERROR" in text or code for code, text in cls.results):
            assert cls.folder.resolve().is_relative_to(ROOT) and cls.folder.resolve() != ROOT
            shutil.rmtree(cls.folder)

    @classmethod
    def mutate(cls):
        # Different values, strings, extra/missing effects, missing placements,
        # empty slots and a changed script layout in one hostile input fixture.
        for name in ["joril", "ilmadia", "idol", "icasa", "dlsgem", "lordm", "kaorog", "kaoroge", "belhif"]:
            p = cls.ov / (name + ".cre")
            d = bytearray(p.read_bytes())
            struct.pack_into("<HH", d, 0x24, 999, 999)
            d[0x52:0x54] = bytes([1, 5])
            d[0x20:0x24] = b"TEST"
            if name == "idol":
                # Delete the old effect table. The owned movement effect must return.
                struct.pack_into("<I", d, 0x2c8, 0)
            p.write_bytes(d)
        for name in ["sarunpr", "dwsaru0"]:
            p = cls.ov / (name + ".cre")
            if p.exists():
                d = bytearray(p.read_bytes()); d[0x53] = 3; p.write_bytes(d)
        for folder in (ROOT / "chriz-iwd-encounters/actors").iterdir():
            p = cls.ov / (folder.name + ".are")
            d = bytearray(p.read_bytes())
            # Keep partial tables for the two regression cases below. Other areas
            # still exercise restoration of entirely missing actor tables.
            if folder.name.lower() not in {"ar7004", "ar8011"}:
                struct.pack_into("<H", d, 0x58, 0)
            d[0x94:0x9c] = bytes(8)
            d[0xe4:0xe4 + len(cls.sentinel)] = cls.sentinel
            p.write_bytes(d)

        for name, field, fmt in [("ar4005", 0x5a, "H"), ("ar8012", 0xa4, "I")]:
            p = cls.ov / (name + ".are"); d = bytearray(p.read_bytes())
            struct.pack_into("<" + fmt, d, field, 0); p.write_bytes(d)
        for name in ["ar2100", "ar4005", "ar8012", "ar1103", "bamemba", "bawail0", "ldidol", "eebelkil", "ildrgded", "eelpomab"]:
            p = cls.ov / (name + ".bcs")
            if p.exists():
                p.write_bytes(b"SC\nSC\n")
        for name in ["kuatkeff", "kuatkrem", "kuatkoro", "gnt2016", "gnt2017", "ldbdgopn", "shelfps1", "cajsha1m"]:
            p = cls.ov / (name + ".bcs")
            if p.exists():
                p.unlink()
        p = cls.ov / "ar9400.ini"
        text = p.read_text()
        text = re.sub(r"(?ims)^\[Virgin01\].*?(?=^\[|\Z)", "", text)
        text = re.sub(r"(?im)^script_override[^\r\n]*", "script_override=EDITED", text)
        p.write_text(text)
        # Missing owned symbol, and a cleric that no longer matches its sibling.
        p=cls.ov/"spell.ids"
        text=re.sub(r"(?im)^.*INNATE_BELHIFETS_DEATH_ANIMATION[^\r\n]*[\r\n]*", "", p.read_text())
        p.write_text(text)
        p=cls.ov/"sdelfch2.cre"; d=bytearray(p.read_bytes())
        d[0x272:0x274]=bytes([1,1]); d[0x234:0x237]=bytes([3,5,9])
        struct.pack_into("<I",d,0x244,0x4000)
        struct.pack_into("<H",d,0x24,321)
        d[0x268:0x270]=b"EDITED\0\0"
        p.write_bytes(d)
        # The mod must not match prose or a description's language.
        for name in ["sppr503", "ohpomill"]:
            p = cls.ov / (name + ".spl"); d = bytearray(p.read_bytes())
            struct.pack_into("<II", d, 8, 777, 888)
            p.write_bytes(d)

    @classmethod
    def compile_scripts(cls, scripts):
        source = cls.game / "fixture-scripts"
        source.mkdir()
        for name, text in scripts.items():
            (source / (name + ".baf")).write_text(text, encoding="ascii")
        (cls.game / "fixture-scripts.tp2").write_text(
            'BACKUP ~fixture-backup~\nAUTHOR ~fixture~\n'
            'BEGIN ~fixture scripts~\nCOMPILE ~fixture-scripts~\n', encoding="ascii")
        result = subprocess.run([WEIDU, "fixture-scripts.tp2", "--force-install-list", "0",
            "--no-exit-pause", "--quick-log", "--use-lang", "en_us"],
            cwd=cls.game, capture_output=True, text=True)
        output = result.stdout + result.stderr
        (cls.folder / "fixture-scripts.log").write_text(output, encoding="utf-8")
        if result.returncode or re.search(r"\b(?:ERROR|WARNING)\b", output):
            raise RuntimeError(output)

    @classmethod
    def review_fixtures(cls):
        if SCENARIO not in {"edited", "embedded"}:
            return
        scripts = {
            "TSTPLAT": '''IF
  Global("TEST_PLATE_FIRST","LOCALS",0)
THEN
  RESPONSE #100
    SetGlobal("TEST_PLATE_FIRST","LOCALS",1)
    Continue()
END
IF
  Global("TEST_PLATE_SECOND","LOCALS",0)
THEN
  RESPONSE #100
    SetGlobal("TEST_PLATE_SECOND","LOCALS",1)
    Continue()
END
''',
            "TSTCOURT": '''IF
  Global("TEST_COURT_AI","LOCALS",0)
THEN
  RESPONSE #100
    SetGlobal("TEST_COURT_AI","LOCALS",1)
    Continue()
END
''',
            "TSTPOM": '''IF
  HPLT(Myself,50)
THEN
  RESPONSE #100
    ApplySpellRES("CDHP3000",Myself)
END
IF
  HPLT(Myself,25)
THEN
  RESPONSE #100
    ApplySpellRES("CDHP3000",Myself)
    JumpToPoint([100.100])
END
IF
  Global("TEST_POM_PRESERVED","LOCALS",0)
THEN
  RESPONSE #100
    SetGlobal("TEST_POM_PRESERVED","LOCALS",1)
    Continue()
END
''',
        }
        if SCENARIO == "embedded":
            # A distinct selected SCS-style melee script, not the CIEMEL fallback.
            scripts["DWMESSGE"] = '''IF
  Global("DMWW_genai_difficulty","GLOBAL",0)
  Global("TEST_SELECTED_MELEE","LOCALS",0)
THEN
  RESPONSE #100
    SetGlobal("TEST_SELECTED_MELEE","LOCALS",1)
    Continue()
END
IF
  See(NearestEnemyOf(Myself))
THEN
  RESPONSE #100
    AttackReevaluate(NearestEnemyOf(Myself),17)
END
'''
        else:
            (cls.ov / "dwmessge.bcs").unlink(missing_ok=True)
        cls.compile_scripts(scripts)
        for name in ("keanimph", "keanimp2"):
            p = cls.ov / (name + ".cre"); data = bytearray(p.read_bytes())
            data[0x260:0x268] = b"TSTPLAT\0"
            p.write_bytes(data)
        p = cls.ov / "eepomab.cre"; data = bytearray(p.read_bytes())
        data[0x248:0x250] = b"TSTPOM\0\0"
        p.write_bytes(data)

        p = cls.ov / "zombiel.cre"
        if SCENARIO == "edited":
            p.unlink()
        else:
            cls.short_zombie = p.read_bytes()[:0x25c]
            p.write_bytes(cls.short_zombie)

        if SCENARIO != "edited":
            return
        p = cls.ov / "ar8011.are"; data = bytearray(p.read_bytes())
        rows = [bytearray(r) for r in actor_rows(data)]
        priests = [i for i, r in enumerate(rows) if check.resref(r, 0x80) == "DROWPM"]
        assert len(priests) == 2
        rows[priests[0]][:32] = b"TEST_RENAMED_PRIEST".ljust(32, b"\0")
        struct.pack_into("<I", rows[priests[0]], 0x28, long(rows[priests[0]], 0x28) | 8)
        cls.renamed_priest_position = bytes(rows[priests[0]][0x20:0x28])
        del rows[priests[1]]
        cls.unrelated_actor = next(bytes(r) for r in rows if check.resref(r, 0x80) == "SALAMAND")
        struct.pack_into("<IH", data, 0x54, len(data), len(rows))
        data += b"".join(rows)
        p.write_bytes(data)

        p = cls.ov / "ar7004.are"; data = bytearray(p.read_bytes())
        cls.court_slots = {}
        for i, row in enumerate(actor_rows(data)):
            if check.resref(row, 0x80) not in {"JORIL", "GIANTFS", "GIANTFG"}:
                continue
            at = long(data, 0x54) + i * 0x110
            data[at + 0x50:at + 0x80] = bytes(0x30)
            # One occupied unrelated slot plus either a gate or a team. Neither
            # must prevent restoration of the missing WTGIANT1 default slot.
            general = "TSTCOURT" if i % 3 == 2 else ""
            data[at + 0x58:at + 0x60] = general.encode("ascii").ljust(8, b"\0")
            gate = b"EFDELDEF" if i % 2 else b"GNTEAM1M"
            data[at + 0x78:at + 0x80] = gate
            cls.court_slots[i] = (actor_name(row), general, gate.decode("ascii"))
        p.write_bytes(data)

    @classmethod
    def embed(cls):
        cls.embedded_names = [("AR7004","JORIL",185),("AR8011","ILMADIA",135),
                              ("AR8012","IDOL",225),("AR9712","LORDM",350),("AR8013","POQUELIN",420)]
        for area, creature, hp in cls.embedded_names:
            p=cls.ov/(area.lower()+".are"); d=bytearray(p.read_bytes())
            actors=long(d,0x54)
            for i in range(word(d,0x58)):
                a=actors+0x110*i
                if check.resref(d,a+0x80)==creature:
                    cre=bytearray((cls.ov/(creature.lower()+".cre")).read_bytes())
                    struct.pack_into("<HH",cre,0x24,999,999)
                    cre[0x20:0x24]=b"EMBD"
                    # An unrelated opcode-101 immunity must survive Poquelin's
                    # owned protections; include duplicates of an owned effect.
                    if creature=="POQUELIN":
                        size=0x108 if cre[0x33]==1 else 0x30
                        effects=long(cre,0x2c4); count=long(cre,0x2c8)
                        rows=cre[effects:effects+count*size]
                        for op in (13,13,28):
                            fx=bytearray(size)
                            if size==0x108:
                                struct.pack_into("<IIIii",fx,8,101,1,0,0,op)
                            else:
                                struct.pack_into("<HBBii",fx,0,101,1,0,0,op)
                            rows+=fx
                        struct.pack_into("<II",cre,0x2c4,len(cre),count+3)
                        cre+=rows
                    d[a+0x50:a+0x80]=bytes(0x30)
                    struct.pack_into("<I",d,a+0x28,long(d,a+0x28)&~1)
                    struct.pack_into("<II",d,a+0x88,len(d),len(cre))
                    d+=cre
                    break
            p.write_bytes(d)

    @classmethod
    def install(cls):
        result = subprocess.run([WEIDU, "chriz-iwd-encounters/setup-chriz-iwd-encounters.tp2",
            "--force-install-list", *map(str, COMPONENTS), "--language", "0", "--use-lang", "en_us",
            "--no-exit-pause", "--quick-log"], cwd=cls.game, capture_output=True, text=True)
        text = result.stdout + result.stderr
        cls.results.append((result.returncode, text))
        (cls.folder / ("install-%d.log" % len(cls.results))).write_text(text)
        cls.res = check.Resources(str(cls.game))

    def script(self, name):
        return (self.res.get(name, "BCS") or b"").lower().replace(b"\r\n", b"\n")

    def area_script(self, area):
        return self.script(check.slot(self.res.get(area, "ARE"), 0x94))

    def test_01_no_warning_or_refusal(self):
        code, text = self.results[-1]
        self.assertEqual(code, 0, text[-6000:])
        self.assertNotRegex(text, r"(?i)\b(?:ERROR|WARNING)\b")
        self.assertEqual(text.count("SUCCESSFULLY INSTALLED"), 15)
        if SCENARIO in {"base","stack"}:
            checked=subprocess.run([sys.executable,"-I",str(ROOT/"tests/check_install.py"),str(self.game)],capture_output=True,text=True)
            (self.folder/("check-%d.log"%len(self.results))).write_text(checked.stdout,encoding="utf-8")
            if checked.returncode:
                type(self).validation_failed=True
                print("Retained fixture:",self.folder,flush=True)
            self.assertEqual(checked.returncode,0,"\n".join(line for line in checked.stdout.splitlines() if line.startswith("FAIL")))
            print("installed-output checks:",checked.stdout.count("PASS  "),flush=True)

    def test_02_decided_creature_fields(self):
        for name, hp in [("JORIL",185),("ILMADIA",135),("IDOL",225),("ICASA",650),
                         ("DLSGEM",250),("LORDM",350),("KAOROG",45),("KAOROGE",70),("CIEPOQ",420),("CIESENTR",240)]:
            with self.subTest(name=name):
                d = self.res.get(name,"CRE")
                self.assertEqual((word(d,0x24), word(d,0x26)), (hp,hp))
                if SCENARIO == "edited" and name not in {"CIEPOQ","CIESENTR"}:
                    self.assertEqual(d[0x20:0x24], b"TEST")
        if SCENARIO=="edited":
            donor=self.res.get("SDELFCH1","CRE"); repaired=self.res.get("SDELFCH2","CRE")
            self.assertEqual(check.slot(repaired,0x268),"SHELFCS1")
            self.assertEqual(repaired[0x272:0x274],bytes([1,1]))
            self.assertEqual(word(repaired,0x24),321)
            self.assertIn(b"cie_self",self.script("SHELFPS1"))
            self.assertIn(b"cie_self",self.script("CAJSHA1M"))
            self.assertIn(b"INNATE_BELHIFETS_DEATH_ANIMATION",self.res.get("SPELL","IDS"))
        self.assertIn((126,0,1,""),check.cre_effects(self.res.get("IDOL","CRE")))
        self.assertEqual(self.res.get("KAOROGE","CRE")[0x52:0x54], bytes([10,2]))

        if SCENARIO=="embedded":
            for area,creature,hp in self.embedded_names:
                d=self.res.get(area,"ARE"); o=long(d,0x54)
                for i in range(word(d,0x58)):
                    a=o+0x110*i
                    if check.resref(d,a+0x80) in {creature,"CIEPOQ"}:
                        emb=long(d,a+0x88)
                        cre=d[emb:emb+long(d,a+0x8c)] if emb else self.res.get(check.resref(d,a+0x80),"CRE")
                        self.assertEqual((word(cre,0x24),word(cre,0x26)),(hp,hp))
                        self.assertEqual(cre[0x20:0x24],b"EMBD")
                        if creature=="IDOL": self.assertIn((126,0,1,""),check.cre_effects(cre))
                        if creature=="POQUELIN":
                            effects=check.cre_effects(cre)
                            self.assertEqual(sum(e[0]==101 and e[2]==13 for e in effects),1)
                            self.assertIn((101,0,28,""),effects)
                        break

    def test_03_missing_encounter_blocks(self):
        for area, markers in [("AR2100",[b"kaorog",b"kaoroge",b"cie_kul_wave"]),
             ("AR4005",[b"cieyxm1",b"cieyxm2",b"cieyxm3",b"yxun_attack"]),
             ("AR9400",[b"cie_meb_guard",b"barrowwight",b"drowneddead"]),
             ("AR8012",[b"cie_idol_rally"]), ("AR9712",[])]:
            for marker in markers:
                self.assertIn(marker,self.area_script(area),(area,marker))
        idol=next(p for p in check.are_actors(self.res.get("AR8012","ARE")).values() if p["cre"]=="IDOL")
        text=b"".join(self.script(s) for s in idol["scripts"].values() if s)
        self.assertIn(b"cie_idol_cast",text)
        self.assertIn(b"cie_idol_death",text)

    def test_04_actor_region_door_tables(self):
        for folder in (ROOT/"chriz-iwd-encounters/actors").iterdir():
            d=self.res.get(folder.name,"ARE"); actors=check.are_actors(d)
            for p in folder.glob("*.actor"):
                name=p.read_bytes()[:32].split(b"\0")[0].decode().upper()
                # Existing named placements may legitimately have renamed identities.
                if SCENARIO=="edited":
                    if folder.name.lower() == "ar8011" and p.name == "027.actor":
                        name = "TEST_RENAMED_PRIEST"
                    self.assertIn(name,actors)
            if SCENARIO=="edited": self.assertEqual(d[0xe4:0xe4+len(self.sentinel)],self.sentinel)
        for area,off,cnt,size in [("AR4005",0x5c,0x5a,0xc4),("AR8012",0xa8,0xa4,0xc8)]:
            d=self.res.get(area,"ARE"); o=long(d,off); n=word(d,cnt) if cnt==0x5a else long(d,cnt)
            self.assertGreaterEqual(n,3 if cnt==0x5a else 7)
            self.assertLessEqual(o+n*size,len(d))
            vertices=long(d,0x7c); count=word(d,0x80)
            self.assertLessEqual(vertices+count*4,len(d))
            for i in range(n):
                row=o+i*size
                for first,number in ([(0x2c,0x2a)] if cnt==0x5a else [(0x2c,0x30),(0x34,0x32),(0x48,0x4c),(0x50,0x4e)]):
                    self.assertLessEqual(long(d,row+first)+word(d,row+number),count)

    def test_05_owned_spell_effects(self):
        effects=check.spl_ability_effects(self.res.get("CIEBELPR","SPL"))
        self.assertEqual({e[1] for e in effects if e[0]==102},{1,2,3})
        self.assertTrue(set(check.BELHIFET_BLOCKED) <= {e[2] for e in effects if e[0]==101})
        self.assertIn((321,0,0,"OHPOMREV"),check.spl_ability_effects(self.res.get("CIEPOMRC","SPL")))
        self.assertIn(276,[e[0] for e in check.spl_ability_effects(self.res.get("CIEPOMIL","SPL"))])

    def test_06_hit_counters_and_gates(self):
        blocks=re.findall(rb"cr\n(.*?)cr\n",self.area_script("AR1103"),re.S)
        counters=[b for b in blocks if b'"globalsprite_is_deadfake_pomab"' in b.split(b"rs\n",1)[-1]
                  and b'"myareacie_pom_shuffle"' in b.split(b"rs\n",1)[-1]]
        self.assertEqual(len(counters),5)
        text=(self.ov/"ar9400.ini").read_text()
        self.assertIn("[virgin01]",text.lower())
        for section in ["virgin01","virgin03","ddead05","bwight25"]:
            body=re.search(r"(?ims)^\["+section+r"\](.*?)(?=^\[|\Z)",text)[1]
            script=re.search(r"(?im)^script_override\s*=\s*(\w+)",body)[1]
            self.assertIn(b"efdel",self.script(script))

    def test_07_cutscene_actions(self):
        self.assertIn(b"cie_cornugon_3",self.script("EEBELKIL"))
        self.assertNotIn(b'"ring91"',self.script("ILDRGDED"))
        # The ending must still enter its cutscene context and finish it.
        text=self.script("EEBELKIL")
        self.assertIn(b'"tower"',text)
        self.assertIn(b'"credits"',text)

    def test_08_partial_and_renamed_actors(self):
        rows = actor_rows(self.res.get("AR8011", "ARE"))
        priests = [r for r in rows if check.resref(r, 0x80) == "DROWPM"]
        self.assertEqual(len(priests), 2)
        self.assertEqual(len({actor_name(r) for r in priests}), 2)
        self.assertEqual(len({r[0x20:0x28] for r in priests}), 2)
        if SCENARIO == "edited":
            renamed = next(r for r in priests if actor_name(r) == "TEST_RENAMED_PRIEST")
            self.assertEqual(renamed[0x20:0x28], self.renamed_priest_position)
            self.assertIn(self.unrelated_actor, rows)
            court = actor_rows(self.res.get("AR7004", "ARE"))
            for index, (name, general, gate) in self.court_slots.items():
                with self.subTest(actor=name, index=index):
                    self.assertEqual(check.slot(court[index], 0x58), general)
                    self.assertEqual(check.slot(court[index], 0x78), gate)
                    self.assertEqual(check.slot(court[index], 0x70), "WTGIANT1")
            self.assertIn(b"test_court_ai", self.script("TSTCOURT"))
            self.assertIn(b"cie_jor_hold", self.script("WTGIANT1"))
            self.assertIn(b"cie_jor_rage", self.script("WTGIANT1"))

    def test_09_absent_or_short_zombie(self):
        data = self.res.get("ZOMBIEL", "CRE")
        message = "chriz-iwd-encounters: zombiel.cre"
        if SCENARIO == "edited":
            self.assertIsNone(data)
            self.assertEqual(self.results[-1][1].count(message), 1)
        elif SCENARIO == "embedded":
            self.assertEqual(data, self.short_zombie)
            self.assertEqual(self.results[-1][1].count(message), 1)
        else:
            self.assertEqual(check.slot(data, 0x258), "ZLAURA")
        self.assertTrue(self.script("ZLAURA"))
        self.assertEqual(word(self.res.get("IDOL", "CRE"), 0x26), 225)
        self.assertIn(b"all_keys", self.script("CIEBDG1"))

    def test_10_no_pomab_self_heal(self):
        data = self.res.get("EEPOMAB", "CRE")
        for at in range(0x248, 0x270, 8):
            self.assertNotIn(b"cdhp3000", self.script(check.slot(data, at)))
        if SCENARIO in {"edited", "embedded"}:
            self.assertIn(b"test_pom_preserved", self.script("TSTPOM"))

    def test_11_selected_melee_keeps_script_order(self):
        for name, (expected, default) in self.plate_expected.items():
            data = self.res.get(name, "CRE")
            script = check.slot(data, 0x260)
            self.assertEqual(script_blocks(self.res.get(script, "BCS")), expected, (name, self.selected_melee))
            self.assertEqual(data[0x268:0x270], default)

    def actor_script_snapshot(self):
        areas = {}
        scripts = set()
        for folder in (ROOT / "chriz-iwd-encounters/actors").iterdir():
            rows = actor_rows(self.res.get(folder.name, "ARE"))
            areas[folder.name] = rows
            scripts.update(check.slot(row, at) for row in rows for at in range(0x50, 0x80, 8))
        for name in ("KEANIMPH", "KEANIMP2", "EEPOMAB"):
            data = self.res.get(name, "CRE")
            scripts.update(check.slot(data, at) for at in range(0x248, 0x270, 8))
        return areas, {s: script_blocks(self.res.get(s, "BCS") or b"") for s in scripts if s}

    def test_12_second_install(self):
        before={n:self.res.get(n,"SPL") for n in ["CIEBELPR","CIEBELHA","CIEPOMRC","CIEPOMIL"]}
        actors, scripts = self.actor_script_snapshot()
        self.install()
        self.test_01_no_warning_or_refusal()
        self.test_02_decided_creature_fields()
        self.test_06_hit_counters_and_gates()
        self.test_08_partial_and_renamed_actors()
        self.test_09_absent_or_short_zombie()
        self.test_10_no_pomab_self_heal()
        self.test_11_selected_melee_keeps_script_order()
        for name,data in before.items(): self.assertEqual(data,self.res.get(name,"SPL"),name)
        after_actors, after_scripts = self.actor_script_snapshot()
        for area, rows in actors.items():
            self.assertEqual(after_actors[area], rows, area)
        self.assertEqual(set(after_scripts), set(scripts))
        for name, blocks in scripts.items():
            self.assertEqual(after_scripts[name], blocks, name)


if __name__=="__main__":
    print("Scenario:",SCENARIO,flush=True)
    unittest.main(verbosity=2)
