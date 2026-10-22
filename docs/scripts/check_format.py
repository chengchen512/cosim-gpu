#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Check repository-specific documentation formatting rules.

Rules:
- every page starts with the Apache-2.0 SPDX identifier;
- exactly one H1 per page and heading depth at most H3;
- an explicit RST label near the top of every page;
- no tabs, CRLF, trailing whitespace, or missing final newline;
- no retired first-line language links and no P0 stub markers;
- index pages that contain a toctree stay navigation-sized (<= 120 lines).

RST syntax itself is checked by sphinx-lint in docs/scripts/check_format.sh.
"""

from __future__ import annotations

import sys
from pathlib import Path

SPDX_TAG = "SPDX-License-" + "Identifier"
SPDX_LINE = ".. " + SPDX_TAG + ": " + "Apache-2.0"
ADORNMENTS = "=-~^\"'"
MAX_HEADING_LEVEL = 3
MAX_INDEX_LINES = 120


def heading_levels(text: str) -> list[int]:
    lines = text.splitlines()
    levels: list[int] = []
    for index in range(1, len(lines)):
        underline = lines[index].rstrip()
        title = lines[index - 1].strip()
        if not title or not underline:
            continue
        if len(set(underline)) != 1 or underline[0] not in ADORNMENTS:
            continue
        if len(underline) < len(title):
            continue
        levels.append(ADORNMENTS.index(underline[0]) + 1)
    return levels


def check_page(path: Path, docs_root: Path) -> list[str]:
    failures: list[str] = []
    raw = path.read_bytes()
    rel = path.relative_to(docs_root)
    text = raw.decode("utf-8")

    if b"\r\n" in raw:
        failures.append(f"{rel}: CRLF line endings")
    if not text.startswith(SPDX_LINE + "\n"):
        failures.append(f"{rel}: missing first-line SPDX identifier")
    if "\t" in text:
        failures.append(f"{rel}: tab character")
    if any(line.rstrip() != line for line in text.splitlines()):
        failures.append(f"{rel}: trailing whitespace")
    if not text.endswith("\n"):
        failures.append(f"{rel}: missing final newline")
    if text.endswith("\n\n"):
        failures.append(f"{rel}: more than one final newline")
    if any(line.startswith(("[English](", "[中文](")) for line in text.splitlines()):
        failures.append(f"{rel}: retired first-line language link")
    for marker in ("P0 骨架", "P0 skeleton"):
        if marker in text:
            failures.append(f"{rel}: unfinished stub marker {marker!r}")

    lines = text.splitlines()
    head = lines[:25]
    if not any(line.startswith(".. _") for line in head):
        failures.append(f"{rel}: missing RST label near the top")

    levels = heading_levels(text)
    if levels.count(1) != 1:
        failures.append(f"{rel}: expected exactly one H1, found {levels.count(1)}")
    if any(level > MAX_HEADING_LEVEL for level in levels):
        failures.append(f"{rel}: heading deeper than H{MAX_HEADING_LEVEL}")

    if path.name == "index.rst" and ".. toctree::" in text:
        if len(lines) > MAX_INDEX_LINES:
            failures.append(
                f"{rel}: navigation index has {len(lines)} lines "
                f"(limit {MAX_INDEX_LINES})"
            )
    return failures


def main() -> int:
    docs_root = Path(__file__).resolve().parents[1]
    failures: list[str] = []
    checked = 0
    for lang in ("zh", "en"):
        for path in sorted((docs_root / lang).rglob("*.rst")):
            checked += 1
            failures.extend(check_page(path, docs_root))
    if failures:
        print(f"documentation format check FAILED ({len(failures)} issue(s)):")
        for failure in failures:
            print("  -", failure)
        return 1
    print(f"documentation format check OK ({checked} pages)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
