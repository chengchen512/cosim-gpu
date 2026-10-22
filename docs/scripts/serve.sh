#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Serve the built documentation site for local preview.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORT=8010
if [ "$#" -ge 1 ]; then PORT=$1; fi
cd "$ROOT/_build/html"
exec python3 -m http.server "$PORT" --bind 127.0.0.1
