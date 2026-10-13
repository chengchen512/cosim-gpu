# SPDX-License-Identifier: Apache-2.0
#
# Task runner for cosim-gpu, the bridge that boots an AI infrastructure
# learning environment in QEMU and backs its accelerators with simulated
# GPU, NPU and TPU models (gem5 MI300X is the GPU backend).
# Run `just` to list the recipes.

set shell := ["bash", "-euo", "pipefail", "-c"]
set positional-arguments

gem5_run_image := env("GEM5_RUN_IMAGE", "gem5-run:local")
gpu_fs_image := env("GPU_APP_BUILD_IMAGE", "ghcr.io/gem5/gpu-fs:latest")
build_jobs := env("JOBS", num_cpus())
m5_dest := "gem5-resources/src/x86-ubuntu-gpu-ml/files/"

# List the available recipes
default:
    @just --list --unsorted

# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

# Initialize the gem5 and gem5-resources submodules
[group('build')]
submodules:
    git submodule update --init --recursive gem5 gem5-resources

# Build the gem5 runtime Docker image (adds json-c for libvfio-user)
[group('build')]
docker-image:
    docker build -t {{ gem5_run_image }} -f scripts/Dockerfile.run scripts

# Build gem5 (VEGA_X86) in the runtime image; use jobs=1 if linking is OOM-killed
[group('build')]
build-gem5 jobs=build_jobs: docker-image
    docker run --rm -u "$(id -u):$(id -g)" \
        -v "$PWD/gem5:/gem5" -w /gem5 {{ gem5_run_image }} \
        scons build/VEGA_X86/gem5.opt -j{{ jobs }}

# Build the m5 utility and install it into the disk image file set
[group('build')]
build-m5: docker-image
    docker run --rm -u "$(id -u):$(id -g)" \
        -v "$PWD/gem5:/gem5" -w /gem5/util/m5 {{ gem5_run_image }} \
        scons build/x86/out/m5
    cp gem5/util/m5/build/x86/out/m5 {{ m5_dest }}

# Build the guest disk image and kernel (needs KVM, system QEMU, ~60 GB disk)
[group('build')]
build-disk:
    ./scripts/run_mi300x_fs.sh build-disk

# Build a GPU application from gem5-resources/src/gpu
[group('build')]
build-app name="square":
    ./scripts/run_mi300x_fs.sh build-app "$1"

# Compile the HIP test kernels under tests/ in the ROCm container
[group('build')]
build-tests:
    docker run --rm -u "$(id -u):$(id -g)" \
        -v "$PWD/tests:/tests" -w /tests {{ gpu_fs_image }} make

# Build everything needed to launch co-simulation
[group('build')]
build-all: build-gem5 build-m5 build-disk build-app

# Show which build artifacts are present
[group('build')]
status:
    ./scripts/run_mi300x_fs.sh status

# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

# Launch QEMU + gem5 co-simulation (options are passed to cosim_launch.sh)
[group('run')]
launch *args:
    ./scripts/cosim_launch.sh "$@"

# Run guest GPU tests in fresh co-simulation sessions (see run_cosim_tests.sh)
[group('run')]
test *args:
    ./scripts/run_cosim_tests.sh "$@"

# List co-simulation resources left on the host without changing them
[group('run')]
preflight:
    ./scripts/cosim_preflight.sh

# Delete orphaned co-simulation resources (sockets, shared memory, containers)
[group('run')]
clean-orphans:
    ./scripts/cosim_launch.sh --force-clean --confirm

# Run standalone gem5 full-system simulation with the stdlib config
[group('run')]
run-fs app="":
    ./scripts/run_mi300x_fs.sh run ${1:+"$1"}

# Run standalone gem5 full-system simulation with the legacy gpufs config
[group('run')]
run-fs-legacy app="":
    ./scripts/run_mi300x_fs.sh run-legacy ${1:+"$1"}

# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

# Run checkpatch.pl on every commit since BASE (default: merge base with origin/main)
[group('check')]
checkpatch base="":
    ./scripts/check_patch.sh ${1:+"$1"}

# Run ShellCheck on the shell scripts
[group('check')]
shellcheck:
    shellcheck scripts/*.sh tests/run_tests.sh tests/test_modprobe_params.sh

# Check that cosim modprobe commands carry the required amdgpu parameters
[group('check')]
modprobe-params:
    bash tests/test_modprobe_params.sh

# Validate MAINTAINERS.yml and require every tracked file to belong to an area
[group('check')]
maintainers-check:
    #!/usr/bin/env bash
    set -euo pipefail
    orphaned="$(python3 scripts/get_maintainer.py orphaned)"
    if [ -n "$orphaned" ]; then
        echo "Files not covered by any area in MAINTAINERS.yml:" >&2
        echo "$orphaned" >&2
        exit 1
    fi
    echo "MAINTAINERS.yml: valid, every tracked file belongs to an area"

# Run all host-side checks that need no submodules, Docker, or KVM
[group('check')]
check: checkpatch shellcheck maintainers-check

# ---------------------------------------------------------------------------
# Maintainers
# ---------------------------------------------------------------------------

# Show the areas, maintainers and collaborators for PATHs
[group('maintainers')]
maintainers +paths:
    @python3 scripts/get_maintainer.py path "$@"

# Show the areas touched by a commit range (default: HEAD~..)
[group('maintainers')]
maintainers-commits range="HEAD~..":
    @python3 scripts/get_maintainer.py commits "$1"

# List all areas with their maintainers and collaborators
[group('maintainers')]
maintainers-areas:
    @python3 scripts/get_maintainer.py areas
