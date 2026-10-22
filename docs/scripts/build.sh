#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Build the cosim-gpu documentation site (zh primary, en translation).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [ -x "$ROOT/.venv/bin/sphinx-build" ]; then
    SPHINX="$ROOT/.venv/bin/sphinx-build"
    PY="$ROOT/.venv/bin/python"
else
    SPHINX="sphinx-build"
    PY="python3"
fi

rm -rf "$ROOT/_build/html"
for lang in zh en; do
    echo "[docs] building $lang"
    COSIM_DOCS_LANG="$lang" "$SPHINX" -W --keep-going -b html \
        -c "$ROOT" "$ROOT/$lang" "$ROOT/_build/html/$lang"
done
"$PY" "$ROOT/scripts/make_landing.py" --out "$ROOT/_build/html"
echo "[docs] done -> $ROOT/_build/html"
