"""Offline format checks for the mod's bundled inputs; no game is opened."""
import importlib.util
import re
import struct
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "chriz-iwd-encounters"
spec = importlib.util.spec_from_file_location("check_install", ROOT / "tests/check_install.py")
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


class Templates(unittest.TestCase):
    def test_actor_records_are_external_named_placements(self):
        for path in (MOD / "actors").glob("*/*.actor"):
            with self.subTest(path=str(path.relative_to(MOD))):
                d = path.read_bytes()
                self.assertEqual(len(d), 0x110)
                self.assertTrue(d[:32].split(b"\0")[0])
                self.assertTrue(check.resref(d, 0x80))
                self.assertEqual(struct.unpack_from("<II", d, 0x88), (0, 0))

    def test_region_vertices_are_local(self):
        for path in (MOD / "placements").glob("*/*.region"):
            d = path.read_bytes()
            count, first = struct.unpack_from("<HI", d, 0x2a)
            self.assertEqual(len(d), 0xc4 + 4 * count)
            self.assertEqual(first, 0)

    def test_door_vertices_are_local(self):
        for path in (MOD / "placements").glob("*/*.door"):
            d = path.read_bytes()
            self.assertEqual((len(d) - 0xc8) % 4, 0)
            for first, count in [(0x2c, 0x30), (0x34, 0x32), (0x48, 0x4c), (0x50, 0x4e)]:
                end = struct.unpack_from("<I", d, first)[0] + struct.unpack_from("<H", d, count)[0]
                self.assertLessEqual(0xc8 + 4 * end, len(d))

    def test_spawn_sections_are_complete(self):
        for path in (MOD / "ini").glob("*.ini"):
            text = path.read_text(encoding="utf-8").lower()
            self.assertIn("[" + path.stem + "]", text)
            for key in ("cre_file", "spec", "spawn_point", "script_override"):
                self.assertRegex(text, r"(?m)^" + key + r"\s*=\s*\S+")

    def test_private_spells_have_complete_effect_tables(self):
        for path in (MOD / "data").glob("*.spl"):
            d = path.read_bytes()
            self.assertEqual(d[:8], b"SPL V1  ")
            abilities = struct.unpack_from("<I", d, 0x64)[0]
            count = struct.unpack_from("<H", d, 0x68)[0]
            effects = struct.unpack_from("<I", d, 0x6a)[0]
            self.assertGreater(count, 0)
            self.assertLessEqual(abilities + count * 0x28, len(d))
            for a in range(count):
                n, first = struct.unpack_from("<HH", d, abilities + a * 0x28 + 0x1e)
                self.assertGreater(n, 0)
                self.assertLessEqual(effects + (first + n) * 0x30, len(d))


if __name__ == "__main__":
    unittest.main(verbosity=2)
