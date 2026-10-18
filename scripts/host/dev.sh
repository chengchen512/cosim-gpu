#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# Run a command on the Host or in a temporary development container.
#
# Usage: scripts/host/dev.sh [--tty] [--mount DIR]... COMMAND [ARG...]
#
# COSIM_ENV selects "host" or "container". Linux defaults to host and other
# systems default to container. The container mounts the source tree, and
# each --mount DIR, at its Host path and is removed when COMMAND exits.

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

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
export COSIM_WORKSPACE="${COSIM_WORKSPACE:-$root}"

if [ "$(uname -s)" = Linux ]; then
    default_env=host
else
    default_env=container
fi
case "${COSIM_ENV:-$default_env}" in
    host)
        export CARGO_HOME="$root/build/dev-cache/host/cargo"
        export CARGO_TARGET_DIR="$root/build/cargo/host"
        export TMPDIR="$root/build/tmp/host"
        mkdir -p "$CARGO_HOME" "$CARGO_TARGET_DIR" "$TMPDIR"
        exec "$@"
        ;;
    container)
        ;;
    *)
        echo "dev.sh: COSIM_ENV must be host or container" >&2
        exit 2
        ;;
esac

image="${COSIM_DEV_IMAGE:-cosim-dev:local}"
if ! docker image inspect "$image" >/dev/null 2>&1; then
    echo "dev.sh: image $image is missing; run 'just dev-image'" >&2
    exit 1
fi

cache="$root/build/dev-cache/container"
target_dir="$root/build/cargo/container"
temp_dir="$root/build/tmp/container"
lock_dir="${COSIM_DISK_LOCK_DIR:-$HOME/.cache/cosim-gpu/disk-locks}"
mkdir -p "$cache/home" "$cache/cargo" "$target_dir" "$temp_dir" "$lock_dir"
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
    --env CARGO_TARGET_DIR="$target_dir"
    --env TMPDIR="$temp_dir"
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

# Docker closes the container's standard input when this client goes away,
# and the launcher ends its session at the end of standard input.
args+=(--interactive --env COSIM_STDIN_LIFELINE=1)
if [ -t 0 ]; then
    exec docker "${args[@]}" "$image" "$@"
fi

# Without a terminal, standard input stays open while this script runs.
docker "${args[@]}" "$image" "$@" < <(
    while kill -0 "$$" 2>/dev/null; do
        sleep 1
    done
) &
client=$!
trap 'kill -TERM "$client" 2>/dev/null' INT TERM
# A trap interrupts wait; wait again until the client has exited.
status=0
wait "$client" || status=$?
while kill -0 "$client" 2>/dev/null; do
    status=0
    wait "$client" || status=$?
done
exit "$status"
