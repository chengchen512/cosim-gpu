#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Verify the generated HTML site (structure, zh-first landing, theme)."""

from __future__ import annotations

import sys
from pathlib import Path

STUB_MARKERS = ("P0 骨架", "P0 skeleton")


def main() -> int:
    repo = Path(__file__).resolve().parents[2]
    docs = repo / "docs"
    html = docs / "_build" / "html"
    failures = []

    if not (html / "index.html").is_file():
        failures.append("missing root landing page")
    elif "zh/index.html" not in (html / "index.html").read_text(encoding="utf-8"):
        failures.append("root landing does not redirect to zh/index.html")

    for lang in ("zh", "en"):
        root = docs / lang
        for source in root.rglob("*.rst"):
            rel = source.relative_to(root).with_suffix(".html")
            target = html / lang / rel
            if not target.is_file():
                failures.append(f"missing HTML: {lang}/{rel}")
        built_pages = list((html / lang).rglob("*.html"))
        if len(built_pages) < 60:
            failures.append(f"too few built pages: {lang} ({len(built_pages)})")
        for page in built_pages:
            text = page.read_text(encoding="utf-8")
            if any(marker in text for marker in STUB_MARKERS):
                failures.append(
                    f"unfinished stub page still present: "
                    f"{page.relative_to(html)}"
                )
        index_html = html / lang / "index.html"
        if index_html.is_file():
            text = index_html.read_text(encoding="utf-8")
            if "zephyr-condensed.css" not in text:
                failures.append(f"theme css not loaded: {lang}")
            if "language-switch.js" not in text:
                failures.append(f"language switcher not loaded: {lang}")

    if failures:
        print(f"site verification FAILED ({len(failures)} issue(s)):")
        for failure in failures:
            print("  -", failure)
        return 1

    print("site verification OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
