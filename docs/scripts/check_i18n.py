#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Check that the Chinese and English documentation trees stay in sync.

Rules:
- every .rst page has a twin with the same relative path in the other tree;
- both twins carry an explicit RST label near the top;
- the heading-level skeleton (sequence of heading levels) matches;
- retired first-line language links are not present.

Exit code 1 when a rule is violated.
"""

from __future__ import annotations

import sys
from pathlib import Path

ADORNMENTS = "=-~^\"'"
ADORNMENT_LEVEL = {char: index for index, char in enumerate(ADORNMENTS)}


def pages(root: Path) -> set[str]:
    return {str(path.relative_to(root)) for path in root.rglob("*.rst")}


def headings(path: Path) -> list[int]:
    lines = path.read_text(encoding="utf-8").splitlines()
    levels = []
    for index in range(1, len(lines)):
        underline = lines[index].rstrip()
        title = lines[index - 1].strip()
        if not title or not underline:
            continue
        if len(set(underline)) != 1 or underline[0] not in ADORNMENT_LEVEL:
            continue
        if len(underline) < len(title):
            continue
        levels.append(ADORNMENT_LEVEL[underline[0]])
    return levels


def has_label(path: Path) -> bool:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith(".. _") and line.rstrip().endswith(":"):
            return True
    return False


def has_legacy_language_link(path: Path) -> bool:
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("[English]") or stripped.startswith("[中文]"):
            return True
    return False


def main() -> int:
    repo = Path(__file__).resolve().parents[2]
    zh_root = repo / "docs" / "zh"
    en_root = repo / "docs" / "en"
    zh_pages = pages(zh_root)
    en_pages = pages(en_root)
    failures = []

    for missing in sorted(zh_pages - en_pages):
        failures.append(f"missing en twin: {missing}")
    for missing in sorted(en_pages - zh_pages):
        failures.append(f"missing zh twin: {missing}")

    for rel in sorted(zh_pages & en_pages):
        zh_file = zh_root / rel
        en_file = en_root / rel
        if not has_label(zh_file):
            failures.append(f"missing label (zh): {rel}")
        if not has_label(en_file):
            failures.append(f"missing label (en): {rel}")
        if has_legacy_language_link(zh_file) or has_legacy_language_link(en_file):
            failures.append(f"legacy first-line language link: {rel}")
        zh_headings = headings(zh_file)
        en_headings = headings(en_file)
        if zh_headings != en_headings:
            failures.append(
                f"heading skeleton differs: {rel} zh={zh_headings} en={en_headings}"
            )

    if failures:
        print(f"i18n check FAILED ({len(failures)} issue(s)):")
        for failure in failures:
            print("  -", failure)
        return 1

    print(f"i18n check OK: {len(zh_pages)} pages per language")
    return 0


if __name__ == "__main__":
    sys.exit(main())
