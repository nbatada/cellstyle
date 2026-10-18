#!/usr/bin/env python3
"""Check/write the R DESCRIPTION snapshot of authoritative root VERSION.

The R package remains independently installable: this repository-only helper is
never required at R installation or runtime.
"""

import argparse
from pathlib import Path
import re


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        parser.error("VERSION must be an R-compatible major.minor.patch version")
    description = root / "r" / "cellstyle" / "DESCRIPTION"
    content = description.read_text(encoding="utf-8")
    matches = list(re.finditer(r"^Version:[^\n]*$", content, re.MULTILINE))
    if len(matches) != 1:
        parser.error("DESCRIPTION must contain exactly one Version field")
    expected = f"Version: {version}"
    if args.write:
        description.write_text(content[:matches[0].start()] + expected + content[matches[0].end():], encoding="utf-8")
    elif matches[0].group() != expected:
        parser.exit(1, "R version snapshot differs from VERSION; run scripts/sync_r_version.py --write\n")
    print(f"R DESCRIPTION version matches VERSION: {version}")


if __name__ == "__main__":
    main()
