<div align="center">
  <h1 align="center">Cosim-GPU</h1>
  <p><strong>YAML-driven QEMU + gem5 co-simulation for AMD MI300X</strong></p>
</div>

<p align="center">
  <img alt="Linux x86_64 and ARM64" src="https://img.shields.io/badge/Linux-x86%5F64%20%7C%20ARM64-FCC624?logo=linux&amp;logoColor=black">
  <img alt="Rust 1.95+" src="https://img.shields.io/badge/Rust-1.95%2B-orange?logo=rust&amp;logoColor=white">
  <img alt="QEMU Device Models" src="https://img.shields.io/badge/QEMU-vfio--user-FF6600">
  <img alt="gem5 MI300X" src="https://img.shields.io/badge/gem5-MI300X-6f42c1">
  <img alt="ROCm HIP" src="https://img.shields.io/badge/ROCm-HIP-ED1C24">
  <img alt="Apache 2.0 license" src="https://img.shields.io/badge/license-Apache--2.0-34a853">
</p>

<p align="center">
  <strong>English</strong> ·
  <a href="README.zh.md">简体中文</a>
</p>

<p align="center">
  <a href="docs/en/getting-started.md">Getting started</a> ·
  <a href="docs/en/topology.md">Topology reference</a> ·
  <a href="docs/en/architecture.md">Architecture</a>
</p>

Define QEMU and Device Model settings in YAML, then launch a session with the
Rust <code>cosim</code> CLI. The Host runs Host-side QEMU and separate gem5 or
QEMU Device Model processes. QEMU uses KVM or TCG to run the vHost OS and
presents each vGPU/vGPGPU through the **vfio-user** interface backed by
libvfio-user.

## Architecture

~~~mermaid
flowchart LR
    YAML[Topology YAML] --> CLI[Rust cosim launcher]

    subgraph Host OS
        CLI --> H[Host-side QEMU]
        CLI --> G[gem5 MI300X Device Model]
        CLI --> Q[QEMU Device Model]
        H <-->|vfio-user / libvfio-user| G
        H <-->|vfio-user| Q
        H --- P[Machine memory pool]
        G --- P
        Q --- P
    end
    H -->|KVM or TCG| V[vHost OS · Linux · ROCm/HIP]
~~~

The launcher prepares shared memory and disk overlays, starts Device Models
before Host-side QEMU, and cleans up the session. Device Models implement the
simulated vGPU/vGPGPU behavior and timing.

## Quick start

~~~bash
just dev-submodules
just dev-image        # Non-Linux Hosts, or set COSIM_ENV=container

# Build the toolchain and x86_64 vHost image on the Host with KVM
just build-all
just run-topology samples/machines/single-gpu.yaml --payload samples/payloads/ubuntu-rocm7_0.yaml
~~~

The first image build uses the selected profile under `resources/images/` and
stores its verified disk and kernel under `build/images/`. Inspect the
resolved profile and launch commands without building or starting processes:

~~~bash
just run-topology samples/machines/single-gpu.yaml --payload samples/payloads/ubuntu-rocm7_0.yaml --dry-run
~~~

### Sample topologies

- <code>samples/machines/single-gpu.yaml</code> — start a single-GPU vHost.
- <code>samples/machines/mixed-models.yaml</code> — combine gem5 and QEMU Device Models.
- <code>samples/machines/gpu-8.yaml</code> — inspect an eight-GPU machine with a 96 GiB memory pool.
- <code>samples/machines/host-only-aarch64.yaml</code> — check an ARM64 vHost without a Device Model.

<details>
<summary>Example: one machine with gem5 and QEMU devices</summary>

~~~yaml
version: 1
imports:
  - hosts/qemu.yaml
  - devices/gpu/mi300x.yaml
  - devices/pci/qemu-edu.yaml
machines:
  - id: m0
    host: {use: host-x86, memory: 32G}
    devices:
      - {use: mi300x, count: 2}
      - {use: qemu-edu}
~~~

Pass `--payload samples/payloads/ubuntu-rocm7_0.yaml` to `just run-topology` to attach the
vHost OS kernel and disk inputs. Build outputs are stored under `build/`.

The QEMU Device Model example serves the real <code>edu</code> PCI model through
<code>x-vfio-user-server</code> from the QEMU built by <code>just build-qemu</code>.

</details>

## Host and build environment

### Launcher and configuration tools

Use Rust 1.95+, Cargo and just for the launcher. Build recipes for QEMU, gem5,
m5, topology runs and Rust checks use <code>scripts/host/dev.sh</code>. On
non-Linux Hosts or with <code>COSIM_ENV=container</code>, they use a temporary
container from <code>scripts/host/Dockerfile.dev</code>. vHost image and HIP builds, plus
<code>just run-launch</code> and <code>just test-gpu</code>, use their own Docker workflows.

### Linux Host sessions

- glibc and <code>setpriv</code> from util-linux.
- QEMU for the Host architecture and <code>qemu-img</code>.
- x86_64 Hosts use <code>qemu-system-x86_64</code>; ARM64 Hosts use
  <code>qemu-system-aarch64</code>.
- <code>COSIM_HOST_ARCH</code> selects the build architecture and defaults to
  the current Host. gem5 builds into
  <code>build/gem5/x86_64/VEGA_X86</code> on x86_64 and
  <code>build/gem5/aarch64/VEGA_X86</code> on ARM64.

### MI300X and QEMU Device Models

- MI300X co-simulation needs gem5 VEGA_X86, QEMU with vfio-user support,
  vHost image inputs, and KVM for the Ubuntu vHost.
- QEMU device servers need a build with
  <code>--enable-vfio-user-server</code>.
- The supplied Ubuntu/ROCm vHost image builder targets x86_64.
- vHost image builds and simulator artifacts need sufficient disk space. The
  memory-pool filesystem must accommodate the complete machine layout.

## Repository map

- **Rust workspace:** <code>crates/cosim-topology/</code>,
  <code>crates/cosim-runtime/</code> and <code>crates/cosim-cli/</code>.
- **Simulation models:** <code>third_party/gem5/</code>,
  <code>third_party/qemu/</code> and <code>configs/sst/</code>.
- **GPU workloads and vHost firmware inputs:** <code>third_party/gem5-resources/</code>.
- **Project tools:** <code>samples/</code>, <code>scripts/</code>,
  <code>justfile</code> and <code>.agents/</code>.
- **vHost image profiles:** <code>resources/images/</code> with Packer/QEMU and
  Ansible recipes for OS base images; image-specific scripts live in each
  profile's <code>files/</code> directory.
- **Shared vHost scripts:** <code>resources/vhost/scripts/</code> for scripts
  used by multiple image profiles.
- **Host and CI scripts:** <code>scripts/host/</code> for Host tools called by
  just, and <code>scripts/ci/</code> for workflow-only helpers and tests.

## More documentation

- [Rust guidelines](docs/en/guidelines.md)
- [Reference](docs/en/reference.md)
- [Contributing](docs/en/contributing.md)

The top-level project uses the [Apache 2.0 license](LICENSE). Submodules retain
their respective licenses.
