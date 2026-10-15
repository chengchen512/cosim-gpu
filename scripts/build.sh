#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# Build simulator components in the current environment.
#
# Usage: scripts/build.sh qemu ARCH JOBS
#        scripts/build.sh gem5 BUILD_DIR JOBS [SCONS_ARG...]
#        scripts/build.sh m5 ABI
#
# Run it through scripts/dev.sh to select the host or the development
# container.

set -euo pipefail

usage() {
    sed -n '4,11s/^# \{0,1\}//p' "${BASH_SOURCE[0]}"
}

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

build_qemu() {
    local arch="$1" jobs="$2"
    local binary="./build/qemu-system-$arch"
    cd "$root/qemu"
    mkdir -p build/scratch
    export TMPDIR="$root/qemu/build/scratch"
    if [ ! -f build/build.ninja ] ||
        ! "$binary" -object help 2>/dev/null |
            grep x-vfio-user-server >/dev/null; then
        (
            cd build
            ../configure --target-list="$arch-softmmu" --enable-kvm \
                --enable-vfio-user-server --disable-docs
        )
    fi
    make -C build -j"$jobs"
    "$binary" -device help | grep vfio-user-pci >/dev/null
    "$binary" -object help | grep x-vfio-user-server >/dev/null
    echo "QEMU built: qemu/build/qemu-system-$arch"
}

build_gem5() {
    local build_dir="$1" jobs="$2"
    shift 2
    cd "$root/gem5"
    mkdir -p "$build_dir/scratch"
    export TMPDIR="$root/gem5/$build_dir/scratch"
    if [ ! -f "$build_dir/gem5.build/config" ]; then
        scons defconfig "$build_dir" build_opts/VEGA_X86
    fi
    scons "$build_dir/gem5.opt" -j"$jobs" "$@"
}

build_m5() {
    local abi="$1"
    cd "$root/gem5/util/m5"
    mkdir -p build/scratch
    TMPDIR="$root/gem5/util/m5/build/scratch" scons "build/$abi/out/m5"
}

case "${1:-}" in
    qemu)
        [ "$#" -eq 3 ] || { usage >&2; exit 2; }
        build_qemu "$2" "$3"
        ;;
    gem5)
        [ "$#" -ge 3 ] || { usage >&2; exit 2; }
        shift
        build_gem5 "$@"
        ;;
    m5)
        [ "$#" -eq 2 ] || { usage >&2; exit 2; }
        build_m5 "$2"
        ;;
    -h | --help)
        usage
        ;;
    *)
        usage >&2
        exit 2
        ;;
esac
