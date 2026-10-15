# SPDX-License-Identifier: Apache-2.0
#
# Task runner for cosim-gpu, the bridge that boots an AI infrastructure
# learning environment in QEMU and backs its accelerators with simulated
# GPU, NPU and TPU models (gem5 MI300X is the GPU backend).
# Run `just` to list the recipes.

set shell := ["bash", "-euo", "pipefail", "-c"]
set positional-arguments

host_arch_input := env("COSIM_HOST_ARCH", arch())
host_arch := if host_arch_input == "aarch64" { "aarch64" } else if host_arch_input == "x86_64" { "x86_64" } else { error("COSIM_HOST_ARCH must be aarch64 or x86_64") }
container_platform := if host_arch == "aarch64" { "linux/arm64" } else { "linux/amd64" }
gem5_build_dir := env("GEM5_BUILD_DIR", "build/" + host_arch + "/VEGA_X86")
dev_image := env("COSIM_DEV_IMAGE", "cosim-dev:local")
gpu_fs_image := env("GPU_APP_BUILD_IMAGE", "ghcr.io/gem5/gpu-fs:latest")
build_jobs := env("JOBS", num_cpus())
m5_abi := if host_arch == "aarch64" { "arm64" } else { "x86" }
m5_dest := env("M5_DEST", if host_arch == "aarch64" { "" } else { "gem5-resources/src/x86-ubuntu-gpu-ml/files/" })

# Recipes that use {{ dev }} run on the host or in a temporary development
# container, as selected by COSIM_ENV.
export COSIM_ENV := env("COSIM_ENV", if os() == "linux" { "host" } else { "container" })
export COSIM_DEV_IMAGE := dev_image
export COSIM_DEV_PLATFORM := container_platform
dev := "scripts/dev.sh"

# List the available recipes
default:
    @just --list --unsorted

# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

# Initialize the qemu, gem5 and gem5-resources submodules
[group('build')]
submodules:
    git submodule update --init --recursive qemu gem5 gem5-resources

# Build the development container image
[group('build')]
dev-image:
    docker build --platform {{ container_platform }} -t {{ dev_image }} -f scripts/Dockerfile.dev scripts

# Open a shell in a temporary development container
[group('build')]
dev-shell:
    COSIM_ENV=container {{ dev }} --tty bash

# Build QEMU with KVM and vfio-user support
[group('build')]
build-qemu jobs=build_jobs:
    {{ dev }} scripts/build.sh qemu {{ host_arch }} "$1"

# Build gem5 (VEGA_X86); use jobs=1 if linking is OOM-killed
[group('build')]
build-gem5 jobs=build_jobs *scons_args:
    {{ dev }} scripts/build.sh gem5 {{ gem5_build_dir }} "$@"

# Build the m5 utility and install it into the disk image file set
[group('build')]
build-m5:
    {{ dev }} scripts/build.sh m5 {{ m5_abi }}
    if [ -n "{{ m5_dest }}" ]; then cp gem5/util/m5/build/{{ m5_abi }}/out/m5 "{{ m5_dest }}"; fi

# Build the guest disk image and kernel (needs KVM, QEMU, ~60 GB disk)
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
build-all: build-qemu build-gem5 build-m5 build-disk build-app

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

# Check gem5 source regions, or entire explicit files, with its style tool
[group('check')]
[working-directory('gem5')]
check-gem5-style *files:
    if [ "$#" -gt 0 ]; then python3 util/style.py "$@" </dev/null; else python3 util/style.py -m $(git diff --name-only -- '*.cc' '*.hh' '*.py') </dev/null; fi

# Inspect gem5 Python formatting without modifying files
[group('check')]
[working-directory('gem5')]
check-gem5-python-format +files:
    python3 -m black --check --diff "$@"
    python3 -m isort --check-only --diff "$@"

# Inspect formatting of staged gem5 C++ changes without modifying files
[group('check')]
[working-directory('gem5')]
check-gem5-cxx-format:
    python3 util/run-git-clang-format.py --dry-run

# Run the gem5 pre-commit hooks for explicit files
[group('check')]
[working-directory('gem5')]
check-gem5-hooks +files:
    pre-commit run --files "$@"

# Validate a gem5 commit message with its repository hook
[group('check')]
[working-directory('gem5')]
check-gem5-message message:
    pre-commit run --hook-stage commit-msg --commit-msg-filename "$1"

# Validate the focused gem5 workflow
[group('check')]
check-gem5-ci:
    actionlint .github/workflows/build.yml gem5/.github/workflows/mi300x-ci.yaml

# Exercise MI300X pool ownership and its GPU_VIPER memory protocol
[group('check')]
test-gem5-mi300x output case="all":
    mkdir -p "$1"
    {{ dev }} --mount "$1" python3 gem5/tests/mi300x/verify.py --gem5 "$PWD/gem5/{{ gem5_build_dir }}/gem5.opt" --output "$(cd "$1" && pwd)" --case "$2"

# Check Rust formatting, warnings and behavior
[group('check')]
check-cosim:
    {{ dev }} cargo fmt --all -- --check
    {{ dev }} cargo clippy --locked --workspace --all-targets -- -D warnings
    {{ dev }} cargo test --locked --workspace

# Inspect Rust formatting without modifying source files
[group('check')]
check-cosim-format:
    {{ dev }} cargo fmt --all -- --check

# Run the Rust tests; arguments are passed to cargo test
[group('check')]
test-cosim *args:
    {{ dev }} cargo test --locked --workspace "$@"

# Run checkpatch.pl on every commit since BASE (default: merge base with origin/main)
[group('check')]
checkpatch base="":
    ./scripts/check_patch.sh ${1:+"$1"}

# Check an uncommitted patch file before creating its signed commit
[group('check')]
checkpatch-file patch:
    perl scripts/checkpatch.pl --no-signoff --no-tree "$1"

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

# Run all host-side checks that need no submodules or KVM
[group('check')]
check: checkpatch shellcheck maintainers-check check-cosim

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
