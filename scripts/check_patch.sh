#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# Run scripts/checkpatch.pl on every non-merge commit in BASE..HEAD.
#
# Usage: scripts/check_patch.sh [BASE]
#
# BASE defaults to the merge base of HEAD and origin/main.

set -euo pipefail

SOURCE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SOURCE_ROOT"

usage() {
    sed -n '4,8s/^# \{0,1\}//p' "${BASH_SOURCE[0]}"
}

case "${1:-}" in
    -h|--help)
        usage
        exit 0
        ;;
esac

if [ "$#" -gt 1 ]; then
    usage >&2
    exit 2
fi

if [ "$#" -eq 1 ]; then
    base_ref="$1"
else
    base_ref="$(git merge-base origin/main HEAD)"
fi

if ! base="$(git rev-parse --verify --quiet "${base_ref}^{commit}")"; then
    echo "check_patch: unknown base revision '$base_ref'" >&2
    exit 2
fi

count="$(git rev-list --count --no-merges "$base..HEAD")"
if [ "$count" -eq 0 ]; then
    echo "No commits since $base, skipping checks"
    exit 0
fi

echo "Checking $count commit(s) since $base..."

# Print only the commits that have problems, with the full hash and the
# offending patch lines.
if ! perl scripts/checkpatch.pl --emacs --quiet --color=never \
        "$base..HEAD"; then
    echo "FAIL: one or more commits failed scripts/checkpatch.pl" >&2
    exit 1
fi

echo "PASS: all commits passed scripts/checkpatch.pl"
