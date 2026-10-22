.. SPDX-License-Identifier: Apache-2.0

.. _ref-topology-schema:

Topology YAML schema
====================

This page is the single source of truth for topology and payload document fields: names, types, defaults, constraints and limits are defined here, and other chapters explain usage and link back. The machine-readable JSON Schema is printed by ``cosim schema``.

Document structure
------------------

A topology document describes hardware and process layout only; guest boot inputs live in a separate payload document. Unknown fields are always errors.

.. list-table::
   :header-rows: 1

   * - Field
     - Type
     - Required
     - Default
     - Constraints
   * - ``version``
     - integer
     - yes
     - —
     - must be ``1``
   * - ``imports``
     - list<string>
     - no
     - ``[]``
     - resolved against the importing file, then ``--samples`` (default ``samples/``); a ``#templates`` suffix is accepted; import cycles are errors
   * - ``templates``
     - map<string, machine/host/device>
     - no
     - ``{}``
     - names are identifiers; mappings merge recursively, sequences are replaced; template cycles are errors
   * - ``kinds``
     - map<string, kind>
     - no
     - ``{}``
     - ``role`` and ``model`` are required; provide ``argv`` or ``command``; ``max_devices`` applies to host kinds
   * - ``machines``
     - list<machine>
     - yes
     - ``[]``
     - at least one machine after imports, templates and ``count`` expansion, otherwise the document is rejected

Machine
-------

A machine is one QEMU host, a set of device processes and one shared memory pool.

.. list-table::
   :header-rows: 1

   * - Field
     - Type
     - Required
     - Default
     - Constraints
   * - ``id``
     - identifier
     - yes
     - —
     - machine identifier; expands to ``id0`` through ``idN`` when ``count`` is greater than 1
   * - ``use``
     - template name
     - no
     - —
     - selects a machine template; unknown references are errors
   * - ``count``
     - positive integer
     - no
     - ``1``
     - expands to multiple machines; the total is capped at 4096
   * - ``host``
     - host
     - yes
     - —
     - see the host field table
   * - ``devices``
     - list<device>
     - no
     - ``[]``
     - bounded by the host kind ``max_devices``; the absolute cap is 256
   * - ``placement.agent``
     - non-empty string
     - no
     - —
     - stored in the plan; ``cosim run`` rejects remote placement

Host
----

A host is the result of merging a host kind declared under ``kinds`` with a template; ``qemu-host`` renders the QEMU command line and declares ``max_devices: 64``.

.. list-table::
   :header-rows: 1

   * - Field
     - Type
     - Required
     - Default
     - Constraints
   * - ``kind``
     - string
     - yes
     - —
     - must resolve to a host kind with ``model: qemu``; only ``qemu-host`` ships
   * - ``runtime.binary``
     - path/name
     - yes
     - —
     - relative to the workspace root, or searched in ``PATH`` when it contains no ``/``
   * - ``runtime.env``
     - map<string,string>
     - no
     - ``{}``
     - the process receives only this environment plus ``PATH`` and ``LANG=C``
   * - ``runtime.argv`` / ``runtime.command``
     - list / string
     - no
     - the kind command template
     - mutually exclusive; override the kind command; strict MiniJinja
   * - ``memory``
     - byte size
     - yes
     - —
     - guest RAM; a multiple of the execution page size
   * - ``memory_align``
     - byte size
     - no
     - 2 MiB
     - alignment of guest RAM in the pool; also the default device-region alignment
   * - ``memory_map``
     - MiniJinja string
     - required with a ``gem5-mi300x`` device
     - —
     - renders 1 to 64 ordered, non-overlapping ranges that cover ``memory`` exactly as ``{start, size}``
   * - ``cpus``
     - positive integer
     - yes
     - —
     - QEMU ``-smp`` value
   * - ``accel``
     - string
     - yes
     - —
     - passed to ``-accel``, for example ``kvm`` or ``tcg``
   * - ``machine``
     - string
     - yes
     - —
     - QEMU machine type, for example ``q35`` or ``virt,gic-version=3``
   * - ``cpu``
     - string
     - no
     - none
     - adds ``-cpu`` when set
   * - ``display`` / ``monitor``
     - string
     - no
     - none
     - QEMU backends; the samples set ``none``
   * - ``no_reboot``
     - bool
     - no
     - ``false``
     - adds ``-no-reboot`` when true
   * - ``serial.wait_for``
     - string
     - no
     - none
     - readiness marker in the serial log
   * - ``serial.timeout``
     - seconds
     - no
     - run-level ``--ready-timeout``
     - requires ``serial.wait_for``; 1 to 86400
   * - ``args``
     - list<string>
     - no
     - ``[]``
     - appended last to the QEMU command line

Device
------

Device fields describe the declaration shape; launch arguments and readiness probes belong to the adapter, see :doc:`device_adapters`.

.. list-table::
   :header-rows: 1

   * - Field
     - Type
     - Required
     - Default
     - Constraints
   * - ``id``
     - identifier
     - no
     - ``use`` name or kind plus ordinal
     - an explicit ``id`` is kept when ``count`` is 1
   * - ``use``
     - template name
     - no
     - —
     - selects a device template
   * - ``kind``
     - string
     - yes
     - —
     - built-in ``gem5-mi300x`` or ``qemu-device``, or a device kind declared under ``kinds``
   * - ``count``
     - positive integer
     - no
     - ``1``
     - expands to multiple device processes
   * - ``config``
     - path
     - required for ``gem5-mi300x``
     - —
     - points to ``mi300_cosim.py``; rejected for ``qemu-device``
   * - ``ready_log``
     - non-empty string
     - required for custom commands
     - the ``gem5-mi300x`` listener line
     - marker printed to standard output once the device listens; must not contain NUL
   * - ``runtime.binary``
     - path/name
     - optional for ``gem5-mi300x``
     - ``gem5.opt``
     - searched in ``PATH`` when omitted; required for the other adapters
   * - ``runtime.env`` / ``argv`` / ``command``
     - map / list / string
     - no
     - —
     - ``argv`` or ``command`` overrides the adapter command
   * - ``memory_regions``
     - list<{name,size,align}>
     - exactly one ``vram`` for ``gem5-mi300x``
     - ``align`` 2 MiB
     - sizes are page multiples; alignment is a power of two of at least one page
   * - ``pci``
     - {vendor_id, device_id, msix_vectors, rom}
     - no
     - —
     - MI300X values are fixed at ``0x1002`` and ``0x74a0`` with 256 MSI-X vectors; provided values must match; ``msix_vectors`` is 1 to 2048
   * - ``args``
     - map<string, any>
     - no
     - ``{}``
     - adapter-specific parameters, see the device adapters page
   * - ``guest_hints``
     - {modprobe, cmdline}
     - no
     - —
     - ``cmdline`` requires a payload with ``boot.kernel``; ``modprobe`` is recorded in the plan only

Payload document
----------------

A payload is chosen independently of the topology and applies to every machine in it. A hardware-only topology may omit the payload; a device that declares ``guest_hints.cmdline`` requires a payload with ``boot.kernel``.

.. list-table::
   :header-rows: 1

   * - Field
     - Type
     - Required
     - Default
     - Notes
   * - ``boot.kernel``
     - path
     - no
     - none
     - enables direct kernel boot; the host adds ``-kernel``
   * - ``boot.initrd``
     - path
     - no
     - none
     - requires ``boot.kernel``
   * - ``boot.cmdline``
     - string
     - no
     - none
     - joined with every device ``guest_hints.cmdline`` value

.. list-table::
   :header-rows: 1

   * - Field
     - Type
     - Required
     - Default
     - Notes
   * - ``id``
     - identifier
     - yes
     - —
     - unique within the payload, ignoring ASCII case
   * - ``path`` / ``backing``
     - path
     - exactly one
     - —
     - ``path`` is the source image; ``backing`` is the overlay base
   * - ``format``
     - ``raw`` / ``qcow2``
     - no
     - ``qcow2``
     - source image format
   * - ``bus``
     - ``virtio`` / ``nvme`` / ``ide`` / ``scsi``
     - no
     - ``virtio``
     - guest attach bus
   * - ``boot``
     - bool
     - no
     - ``false``
     - at most one ``true`` per payload
   * - ``create`` + ``size``
     - bool + byte size
     - no
     - ``false`` / none
     - ``create: true`` requires ``path`` and ``size``; ``size`` is used only when creating
   * - ``readonly`` / ``shared``
     - bool
     - no
     - overlay
     - ``shared: true`` requires ``readonly: true``; direct writes require ``readonly: false`` and ``shared: false``
   * - ``snapshot`` (payload-level)
     - bool
     - no
     - ``false``
     - creates a qcow2 overlay for every machine

``snapshot`` is a payload-level boolean: when true every disk is opened through an overlay, even when ``readonly: false`` and ``shared: false`` are declared.

Resource paths and identifiers
------------------------------

- Resource paths resolve against the workspace root (``COSIM_WORKSPACE``, or the current directory when unset): executables containing ``/``, ``config``, ``pci.rom``, ``boot.kernel``, ``boot.initrd``, and disk ``path`` / ``backing``.

- Relative paths must not contain ``..``; absolute paths are accepted. Executable names without ``/`` are searched in ``PATH``.

- Identifiers are 1 to 48 ASCII letters, digits, underscores or hyphens. Machine, device and disk identifiers must be unique ignoring ASCII case.

- The machine identifier ``memory`` and the device identifiers ``host``, ``qmp`` and ``serial`` are reserved by the session layout.

Defaults and limits
-------------------

.. list-table::
   :header-rows: 1

   * - Item
     - Default or limit
     - Source
   * - Default region alignment
     - 2 MiB
     - ``crates/cosim-topology/src/resolve.rs``
   * - Default disk format / bus
     - ``qcow2`` / ``virtio``
     - ``crates/cosim-topology/src/model.rs``
   * - Maximum machines
     - 4096
     - ``crates/cosim-topology/src/resolve.rs``
   * - Devices per machine
     - host kind ``max_devices`` (64 for ``qemu-host``), absolute cap 256
     - ``crates/cosim-topology/src/resolve.rs``
   * - Identifiers
     - 1 to 48 ASCII letters, digits, ``_`` or ``-``; unique ignoring case
     - ``crates/cosim-topology/src/model.rs``
   * - Reserved names
     - machine ``memory``; device ``host``, ``qmp``, ``serial``
     - ``crates/cosim-runtime/src/layout.rs``
   * - Serial marker timeout
     - 1 to 86400 seconds
     - ``crates/cosim-topology/src/resolve.rs``
   * - Default readiness timeout
     - 120 seconds (``--ready-timeout``)
     - ``crates/cosim-cli/src/main.rs``
   * - Default run directory
     - ``.cosim/<12-hex>``
     - ``crates/cosim-cli/src/main.rs``
   * - Default pool directory
     - ``/dev/shm/cosim-<name>-<hash>`` on Linux, ``<run-dir>/memory`` elsewhere
     - ``crates/cosim-runtime/src/layout.rs``
   * - Disk lock directory
     - ``~/.cache/cosim-gpu/disk-locks`` (``COSIM_DISK_LOCK_DIR``)
     - ``crates/cosim-runtime/src/env.rs``

Sources and maintenance
-----------------------

The field definitions come from these files; update the tables above in the same change:

- ``crates/cosim-topology/src/raw.rs``: YAML decoding types.

- ``crates/cosim-topology/src/model.rs``: validated types and enum values.

- ``crates/cosim-topology/src/resolve.rs``: defaults, constraints and limits.

- ``crates/cosim-runtime/src/layout.rs``: session paths and reserved names.

- ``samples/``: repository tests load and render every sample, so they are live examples of valid configurations.

Verify a change with:

.. code-block:: bash

   just run-cli schema
   just run-cli schema --payload
   just run-cli validate samples/machines/single-gpu.yaml --payload samples/payloads/ubuntu-rocm7_0.yaml --assets
   just check-cosim

Related pages
-------------

- Device launch contracts: :doc:`device_adapters`

- Guest driver parameters: :doc:`guest_parameters`

- Writing topology files: :ref:`topo-write-topology`

- Payloads and guest images: :ref:`topo-payloads`

- YAML loading and planning: :ref:`launcher-yaml-pipeline`
