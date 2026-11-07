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
                if SCENARIO=="edited": self.assertIn(name,actors)
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

    def test_08_second_install(self):
        before={n:self.res.get(n,"SPL") for n in ["CIEBELPR","CIEBELHA","CIEPOMRC","CIEPOMIL"]}
        self.install()
        self.test_01_no_warning_or_refusal()
        self.test_02_decided_creature_fields()
        self.test_06_hit_counters_and_gates()
        for name,data in before.items(): self.assertEqual(data,self.res.get(name,"SPL"),name)


if __name__=="__main__":
    print("Scenario:",SCENARIO,flush=True)
    unittest.main(verbosity=2)
