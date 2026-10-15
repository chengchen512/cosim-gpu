#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# Run a command on the host or in a temporary development container.
#
# Usage: scripts/dev.sh [--tty] [--mount DIR]... COMMAND [ARG...]
#
# COSIM_ENV selects "host" or "container". Linux defaults to host and other
# systems default to container. The container mounts the source tree, and
# each --mount DIR, at its host path and is removed when COMMAND exits.

set -euo pipefail

usage() {
    sed -n '4,10s/^# \{0,1\}//p' "${BASH_SOURCE[0]}"
}

tty=0
mounts=()
while [ "$#" -gt 0 ]; do
    case "$1" in
        --tty)
            tty=1
            shift
            ;;
        --mount)
            [ "$#" -ge 2 ] || { usage >&2; exit 2; }
            mounts+=("$(cd "$2" && pwd)")
            shift 2
            ;;
        *)
            break
            ;;
    esac
done
if [ "$#" -eq 0 ]; then
    usage >&2
    exit 2
fi

if [ "$(uname -s)" = Linux ]; then
    default_env=host
else
    default_env=container
fi
case "${COSIM_ENV:-$default_env}" in
    host)
        exec "$@"
        ;;
    container)
        ;;
    *)
        echo "dev.sh: COSIM_ENV must be host or container" >&2
        exit 2
        ;;
esac

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
image="${COSIM_DEV_IMAGE:-cosim-dev:local}"
if ! docker image inspect "$image" >/dev/null 2>&1; then
    echo "dev.sh: image $image is missing; run 'just dev-image'" >&2
    exit 1
fi

cache="$root/target/dev-cache"
lock_dir="${COSIM_DISK_LOCK_DIR:-$HOME/.cache/cosim-gpu/disk-locks}"
mkdir -p "$cache/home" "$cache/cargo" "$lock_dir"
lock_dir="$(cd "$lock_dir" && pwd)"
name="cosim-dev-$(od -An -N4 -tx1 /dev/urandom | tr -d '[:space:]')"

# tmpfs size is a limit, so /dev/shm may grow to the daemon's memory.
args=(
    run --rm --init --name "$name"
    --user "$(id -u):$(id -g)"
    --shm-size "$(docker info --format '{{.MemTotal}}')"
    --volume "$root:$root" --workdir "$PWD"
    --volume "$lock_dir:$lock_dir"
    --env HOME="$cache/home"
    --env CARGO_HOME="$cache/cargo"
    --env CARGO_TARGET_DIR="$root/target/container"
    --env COSIM_DISK_LOCK_DIR="$lock_dir"
)
if [ -n "${COSIM_DEV_PLATFORM:-}" ]; then
    args+=(--platform "$COSIM_DEV_PLATFORM")
fi
# Bash 3.2 treats an empty array as unset under set -u.
for mount in ${mounts[@]+"${mounts[@]}"}; do
    args+=(--volume "$mount:$mount")
done
while IFS= read -r variable; do
    case "$variable" in
        COSIM_ENV | COSIM_DEV_* | COSIM_DISK_LOCK_DIR) ;;
        COSIM_* | GEM5_* | JOBS | RUST_*) args+=(--env "$variable") ;;
    esac
done < <(compgen -e)
if [ -c /dev/kvm ]; then
    args+=(--device /dev/kvm --group-add "$(stat -c %g /dev/kvm)")
fi

echo "dev.sh: container $name" >&2
if [ "$tty" -eq 1 ]; then
    exec docker "${args[@]}" --interactive --tty "$image" "$@"
fi
exec docker "${args[@]}" "$image" "$@"
