.. SPDX-License-Identifier: Apache-2.0


.. _topo-payloads:

Payloads and guest images
=========================

A payload is a separate YAML document that provides the guest boot inputs: kernel, command line and disks. It is selected with ``--payload`` when validating or running, and applies to every machine in the topology; a hardware-only topology may omit it. This page covers the payload structure, the Ubuntu + ROCm payload shipped with the repository, guest image facts and pairing constraints.

Payload document structure
--------------------------

.. list-table::
   :header-rows: 1

   * - Field
     - Required
     - Default
     - Description
   * - ``version``
     - yes
     - none
     - Must be ``1``
   * - ``boot.kernel``
     - no
     - none
     - Enables direct kernel boot
   * - ``boot.initrd``
     - no
     - none
     - Requires ``kernel``
   * - ``boot.cmdline``
     - no
     - none
     - Space-joined with device ``guest_hints.cmdline``
   * - ``disks[].id``
     - yes
     - none
     - Unique within the payload; identifiers are case-insensitive
   * - ``disks[].path``, ``backing``
     - exactly one
     - none
     - Source image path, or the base image of an overlay
   * - ``disks[].format``
     - no
     - ``qcow2``
     - ``raw`` or ``qcow2``
   * - ``disks[].bus``
     - no
     - ``virtio``
     - ``virtio``, ``nvme``, ``ide`` or ``scsi``
   * - ``disks[].boot``
     - no
     - ``false``
     - At most one boot disk
   * - ``disks[].create`` plus ``size``
     - no
     - ``false``, none
     - Creates a missing image with ``qemu-img``
   * - ``disks[].readonly``, ``shared``
     - no
     - overlay mode
     - Combination rules are in the disk modes section
   * - ``snapshot``
     - no
     - ``false``
     - Forces a per-machine qcow2 overlay

Shipped payload
---------------

.. code-block:: yaml

   # samples/payloads/ubuntu-rocm7_0.yaml
   version: 1
   boot:
     kernel: build/rocm-local-installed/kernel
     cmdline: >-
       console=ttyS0 root=/dev/vda1 rw nokaslr modprobe.blacklist=amdgpu
   disks:
     - id: root
       backing: build/rocm-local-installed/disk
       format: raw
       bus: virtio
       boot: true

- The kernel and disk come from the image build output directory ``build/rocm-local-installed/``.
- ``cmdline`` uses ``ttyS0`` as the console and postpones driver loading with ``modprobe.blacklist=amdgpu``; the guest initialization service loads the driver uniformly.
- The disk declares ``backing`` with the ``raw`` format: the source image is the overlay base and each machine writes its own qcow2 overlay in the session directory.
- The image must be prepared before the first run, see :ref:`gs-guest-image`.

Guest image
-----------

.. list-table::
   :header-rows: 1

   * - Component
     - Value
     - Description
   * - Distribution
     - Ubuntu 24.04.2 LTS
     - The only image recipe lives in ``resources/images/recipes/ubuntu/24.04/x86_64/rocm7_0/``
   * - Kernel
     - 6.8.0-124-generic
     - The ``amdgpu-dkms`` module matches this kernel
   * - ROCm
     - 7.0
     - Installs the ``amdgpu`` and ``rocm`` packages
   * - System disk
     - about 55 GB
     - ``just build-m5`` and ``just build-disk`` produce the kernel and disk
   * - Architecture
     - x86_64
     - There is no AArch64 guest image
   * - initrd
     - not shipped
     - Direct kernel boot uses the paired kernel
   * - Guest initialization
     - ``cosim-gpu-setup.service``
     - Writes the ROM and loads ``amdgpu`` with fixed parameters

- The full image content and build description are in :ref:`gs-guest-image`; the authoritative driver parameters are in :ref:`ref-guest-parameters`, and driver requirements are in :ref:`sim-guest-driver`.
- Kernel and disk must come from the same image build: the DKMS module matches only the paired kernel.

Disk modes
----------

.. list-table::
   :header-rows: 1

   * - Mode
     - Declaration
     - Behavior
   * - Read-only source
     - ``readonly: true``
     - Opens the source image read-only; ``shared: true`` allows several disks to share it
   * - Direct write
     - ``readonly: false`` and ``shared: false``
     - Writes ``path`` directly; the image must not be shared with other disks of the topology
   * - Per-machine overlay
     - No ``readonly``, or ``backing`` declared, or ``snapshot: true``
     - Writes a qcow2 overlay per machine in the session directory; the source image stays unchanged
   * - Create
     - ``create: true`` plus ``size``
     - Creates a missing ``path`` with ``qemu-img``; formats under a temporary name and publishes it with a link

- ``shared: true`` requires ``readonly: true``; ``readonly: false`` requires ``shared: false``.
- The authoritative disk field description is in :ref:`ref-topology-schema`; disk locks and direct-writer exclusivity are described in :ref:`launcher-session-lifecycle`.

Pairing and constraints
-----------------------

- One payload applies to every machine in the topology; the format has no per-machine payload or disk mapping, so a multi-machine topology boots identical disk contents (each machine gets its own overlay).
- Host profiles describe hardware and QEMU settings only; direct kernel boot is enabled only by ``boot.kernel``.
- A device with ``guest_hints.cmdline`` requires a payload with ``boot.kernel``, otherwise validation fails.
- ``boot.cmdline`` and every device ``guest_hints.cmdline`` are space-joined and passed to QEMU ``-append``.
- No initrd is shipped: direct kernel boot relies on the kernel paired with the image.
- The guest image targets x86_64 only; the AArch64 samples do not boot a guest, see :doc:`../machines/aarch64`.
- At runtime the pool, overlays and sockets live in the session directory; source images are opened read-only or held exclusively through image leases.

Related pages
-------------

- Machine catalog: :doc:`../machines/index`
- Single and multi-machine: :doc:`../single_machine`, :doc:`../multi_machine`
- Writing topologies: :doc:`../write_topology`
- Image preparation: :ref:`gs-guest-image`
- Guest parameters: :ref:`ref-guest-parameters`
- Driver requirements: :ref:`sim-guest-driver`
- Sources: ``samples/payloads/ubuntu-rocm7_0.yaml``, ``crates/cosim-topology/src/raw.rs``
