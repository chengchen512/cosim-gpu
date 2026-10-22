.. SPDX-License-Identifier: Apache-2.0


.. _topo-write-topology:

Writing topologies
==================

This page walks through writing a topology document: start from the document skeleton, reuse host and device definitions through imports and templates, expand machine and device counts, and check the result with ``validate``, ``plan`` and ``graph``. The complete field set and defaults are in :ref:`ref-topology-schema`.

Document skeleton
-----------------

A topology document is always ``version: 1`` and may contain ``imports``, ``templates``, ``kinds`` and ``machines``. Unknown fields are errors.

.. code-block:: yaml

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
         - {use: qemu-edu, count: 2}

- Guest boot inputs (kernel, command line, disks) are not in the topology. They live in a payload document selected with ``--payload`` when validating or running; one payload applies to every machine.
- ``cosim schema`` prints the JSON Schema of the topology format, and ``cosim schema --payload`` prints the payload schema.
- Resource paths resolve against the workspace root, including executables containing ``/``, device ``config`` and ``pci.rom``, payload ``boot.kernel`` and ``boot.initrd``, and disk ``path`` and ``backing``. A bare executable name without ``/`` is looked up in ``PATH`` while planning.

Imports and templates
---------------------

- Imports resolve against the importing file, then against the ``--samples`` directory (default ``samples/``); the ``#templates`` suffix is accepted.
- Imported files contribute templates, kinds and further imports; only the top-level document contributes runnable machines.
- ``use`` selects a template; mappings merge recursively, sequences are replaced, and explicit values override template values.
- Import cycles, template cycles, duplicate template or kind names and unknown references are errors; a file reached through several imports is loaded once.
- The repository layout convention: ``samples/hosts/`` and ``samples/devices/`` import nothing, ``samples/machines/`` imports both, and ``samples/clusters/`` imports machine files.

.. code-block:: text

   hosts/ ───┐
   devices/ ─┴──> machines/ ───> clusters/

Machines, devices and count
---------------------------

- ``count`` expands ``id: m, count: 4`` into ``m0`` to ``m3``; a topology holds at most 4096 machines.
- Device identifiers default to the ``use`` name or kind plus an index, such as ``mi300x-0``; an explicit ``id`` is kept when count is one.
- Identifiers use 1 to 48 letters, digits, underscores and hyphens; machine, device and disk identifiers must differ in more than ASCII case.
- The machine identifier ``memory`` and the device identifiers ``host``, ``qmp`` and ``serial`` are reserved by the session layout.
- A machine may not exceed the ``max_devices`` of its host kind; ``qemu-host`` declares 64.
- ``placement.agent`` is parsed and stored only; ``cosim run`` rejects remote placement.

Host and device fields
----------------------

A host declares ``kind``, ``runtime.binary``, ``runtime.env``, ``memory``, ``cpus``, ``accel`` and the QEMU ``machine``. Optional fields are ``cpu``, ``display``, ``monitor``, ``no_reboot``, ``memory_align``, ``memory_map``, ``serial`` and ``args``. A device ``kind`` selects the launch contract:

.. list-table::
   :header-rows: 1

   * - kind
     - Purpose
     - Required fields
   * - ``gem5-mi300x``
     - gem5 MI300X performance model
     - ``config``, exactly one power-of-two ``vram`` region, and the host ``memory_map``
   * - ``qemu-device``
     - QEMU device exported over vfio-user
     - ``runtime.binary`` and ``args.device.driver``; rejects ``config`` and private memory regions
   * - Declared device kind
     - Custom launch command (extension point)
     - ``role: device`` plus ``argv`` or ``command`` under ``kinds``; ``ready_log``

The complete field tables and adapter contracts are in :ref:`ref-topology-schema` and :ref:`ref-device-adapters`; host profiles are in :doc:`hosts/index`, device kinds in :doc:`devices/index`.

Payload and disks
-----------------

A payload document contains ``boot`` (``kernel``, ``initrd``, ``cmdline``), ``disks`` and ``snapshot``. The write mode of a disk follows its declaration:

.. list-table::
   :header-rows: 1

   * - Declaration
     - Behavior
   * - ``readonly: true``
     - Opens the source image read-only
   * - ``readonly: false`` plus ``shared: false``
     - Writes ``path`` directly; with ``backing`` declared or payload ``snapshot: true``, uses a per-machine qcow2 overlay instead
   * - No ``readonly``
     - Writes a per-machine qcow2 overlay in the session directory; ``shared: true`` requires ``readonly: true``
   * - ``create: true`` plus ``size``
     - Creates a missing ``path`` with ``qemu-img``; formats under a temporary name and publishes it with a link
   * - Several disks referencing one path
     - A direct writer cannot share its image with other disks; creation requests must agree on size and format

Payload structure and pairing constraints are in :doc:`payloads/index`; the authoritative disk field description is in :ref:`ref-topology-schema`.

Validating, previewing and running
----------------------------------

.. code-block:: bash

   # Check structure, identifiers and memory layout; --assets also checks local files
   just run-cli validate samples/machines/gpu-8.yaml --payload samples/payloads/ubuntu-rocm7_0.yaml --assets
   # Print executables, arguments, environment, readiness probes, memory layout and disk targets
   just run-cli plan samples/machines/mixed-models.yaml --payload samples/payloads/ubuntu-rocm7_0.yaml
   # Print a Mermaid graph of machines and vfio-user edges
   just run-cli graph samples/clusters/cluster-4x8.yaml
   # Print the JSON Schema of the format
   just run-cli schema
   # Start a session
   just run-topology samples/machines/single-gpu.yaml --payload samples/payloads/ubuntu-rocm7_0.yaml

- ``validate`` starts no processes; ``plan`` prints the plan that ``run`` executes; ``graph`` only reads the document.
- ``--assets`` and a real session start check that files such as ``runtime.binary``, ``config`` and ``pci.rom`` exist.
- Starting a session requires Linux glibc and ``setpriv``; other systems use the development container, see :ref:`gs-platform-container`.

Sources and evidence
--------------------

- Parsing and validation: ``crates/cosim-topology/src/raw.rs``, ``crates/cosim-topology/src/resolve.rs``, ``crates/cosim-topology/src/model.rs``.
- Planning and layout: ``crates/cosim-topology/src/layout.rs``, ``crates/cosim-runtime/src/plan.rs``.
- Command entry point and options: ``crates/cosim-cli/src/main.rs``.
- Runnable samples: ``samples/machines/``, ``samples/clusters/``.

Related pages
-------------

- Single and multi-machine: :doc:`single_machine`, :doc:`multi_machine`
- Machine catalog: :doc:`machines/index`
- Hosts and devices: :doc:`hosts/index`, :doc:`devices/index`
- Payloads: :doc:`payloads/index`
- Schema reference: :ref:`ref-topology-schema`
