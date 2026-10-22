#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Run repository formatting rules and sphinx-lint over the documentation.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

PY="python3"
if [ -x "$ROOT/.venv/bin/python" ]; then PY="$ROOT/.venv/bin/python"; fi
LINT="sphinx-lint"
if [ -x "$ROOT/.venv/bin/sphinx-lint" ]; then LINT="$ROOT/.venv/bin/sphinx-lint"; fi

"$PY" "$ROOT/scripts/check_format.py"
"$LINT" --disable=horizontal-tab,missing-space-before-default-role,trailing-whitespace \
    "$ROOT/zh" "$ROOT/en"
