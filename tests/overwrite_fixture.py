"""Read reference resources into a disposable, data-only WeiDU fixture.

No executable is copied. The source is opened for reading only; all WeiDU work
belongs in the destination, which must be inside this checkout.
"""
import importlib.util
import shutil
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("check_install", ROOT / "tests/check_install.py")
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)
check.EXT.update({0x3F3: "DLG", 0x3F4: "2DA", 0x3F8: "EFF", 0x802: "INI"})


def extract(source, destination, original=False):
    destination = Path(destination).resolve()
    if not destination.is_relative_to(ROOT) or destination == ROOT:
        raise ValueError("Fixture destination must be a child of this checkout")
    if destination.exists():
        raise ValueError("Use a new fixture directory")
    resources = check.Resources(str(source))
    override = destination / "override"
    override.mkdir(parents=True)
    keys = set(resources.biffed)
    if not original:
        keys.update(resources.override)
    keys = sorted((key for key in keys if key[1] in check.EXT.values()),
                  key=lambda key: resources.biffed.get(key, 0) >> 20)
    for name, ext in keys:
        data = resources.original(name, ext) if original else resources.get(name, ext)
        if data is not None:
            (override / (name.lower() + "." + ext.lower())).write_bytes(data)
        if len(resources.biff_cache) > 1:
            last = next(reversed(resources.biff_cache))
            resources.biff_cache = {last: resources.biff_cache[last]}
    (destination / "chitin.key").write_bytes(b"KEY V1  " + struct.pack("<4I", 0, 0, 24, 24))
    (override / "howparty.2da").write_text("2DA V1.0\n0\nVALUE\n", encoding="ascii")
    tlk = b"TLK V1  " + struct.pack("<HII", 0, 1, 44) + bytes(26)
    (destination / "lang/en_us").mkdir(parents=True)
    (destination / "lang/en_us/dialog.tlk").write_bytes(tlk)
    (destination / "dialog.tlk").write_bytes(tlk)
    (destination / "WeiDU.log").touch()
    record = Path(source) / "weidu_external/data/stratagems/genai_scripts_built.txt"
    if not original and record.is_file():
        target = destination / "weidu_external/data/stratagems/genai_scripts_built.txt"
        target.parent.mkdir(parents=True)
        shutil.copyfile(record, target)
    shutil.copytree(ROOT / "chriz-iwd-encounters", destination / "chriz-iwd-encounters")
    return resources


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--original", action="store_true")
    args = parser.parse_args()
    extract(args.source, args.destination, args.original)
    print("Extracted data-only fixture:", args.destination)
