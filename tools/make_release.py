"""Build the release archive of Chriz IWD Encounters from a git tag or commit.

The archive holds one folder, chriz-iwd-encounters/, which is what goes into the
game folder: the WeiDU mod plus its readme, changelog, license, notices and
component notes, laid out so the readme's links still work. Files are taken from
git exactly as stored, entries are uncompressed, sorted and stamped with the
commit time, so the same ref always gives the same bytes.

Usage: python -I tools/make_release.py v0.1.0 chriz-iwd-encounters-v0.1.0.zip
"""

import argparse
import hashlib
import subprocess
import time
import zipfile
from pathlib import Path

MOD = "chriz-iwd-encounters"
DOCS = ("CHANGELOG.md", "LICENSE", "README.md", "THIRD_PARTY_NOTICES.md", "docs/components.md")


def git(repo: Path, *args: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True
    ).stdout


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the release zip from a git ref.")
    parser.add_argument("ref", help="tag or commit to package, e.g. v0.1.0")
    parser.add_argument("output", type=Path, help="zip file to write")
    args = parser.parse_args()

    repo = Path(__file__).resolve().parent.parent
    commit = git(repo, "rev-parse", "--verify", f"{args.ref}^{{commit}}").decode().strip()
    stamp = time.gmtime(int(git(repo, "show", "-s", "--format=%ct", commit)))
    listed = git(repo, "ls-tree", "-r", "-z", "--name-only", commit, "--", MOD)
    sources = {path: path for path in listed.decode().split("\0") if path}
    sources.update({f"{MOD}/{doc}": doc for doc in DOCS})

    with zipfile.ZipFile(args.output, "x") as archive:
        for name in sorted(sources, key=str.casefold):
            info = zipfile.ZipInfo(name, date_time=stamp[:6])
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_STORED
            archive.writestr(info, git(repo, "cat-file", "blob", f"{commit}:{sources[name]}"))

    data = args.output.read_bytes()
    print(f"commit {commit}")
    print(f"entries {len(sources)}")
    print(f"length {len(data)}")
    print(f"sha256 {hashlib.sha256(data).hexdigest()}")


if __name__ == "__main__":
    main()
