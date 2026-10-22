.. SPDX-License-Identifier: Apache-2.0


.. _topo-machines-qemu-device:

qemu-device machine
===================

Overview
--------

The ``qemu-device`` board is a paused x86_64 host plus one QEMU ``edu`` device: the device process runs with ``-machine x-remote`` and exports the ``edu`` PCI device to the host over vfio-user. It validates the QEMU device adapter, the start order of devices and host, socket and QMP probes, and option ROM handling; the board runs no guest.

Topology
--------

.. code-block:: yaml

   # samples/machines/qemu-device.yaml
   version: 1
   imports:
     - hosts/qemu.yaml
     - hosts/host-x86-tcg.yaml
     - devices/pci/qemu-edu.yaml
   machines:
     - id: m0
       host:
         use: host-x86-tcg
         runtime: {binary: build/qemu/qemu-system-x86_64}
     devices:
       - {use: qemu-edu}

- Machine count: one (``m0``); the host overrides ``runtime.binary`` to use the QEMU built from the submodule.
- The device gets the default identifier ``qemu-edu-0`` and has no private memory region.
- The host starts paused with ``-S -nodefaults``; there is no payload.

Hardware resources
------------------

.. list-table::
   :header-rows: 1

   * - Resource
     - Value
     - Source
   * - Machine
     - 1 (``m0``)
     - ``samples/machines/qemu-device.yaml``
   * - Host profile
     - ``host-x86-tcg``: ``q35``, ``tcg``, ``qemu64`` CPU
     - ``samples/hosts/host-x86-tcg.yaml``
   * - Guest RAM
     - 64 MiB, 1 vCPU
     - Same file
   * - Device
     - 1 × ``qemu-edu`` with ``args.device`` set to ``{driver: edu}``
     - ``samples/devices/pci/qemu-edu.yaml``
   * - Memory pool
     - 64 MiB (the device has no private region)
     - Host RAM
   * - Executables
     - ``build/qemu/qemu-system-x86_64`` for both host and device
     - The two templates
   * - Sockets
     - Host QMP and serial; device vfio-user socket and QMP
     - Session layout
   * - Payload
     - None
     - —

Software stack
--------------

.. list-table::
   :header-rows: 1

   * - Layer
     - Component
     - Description
   * - Guest OS
     - None
     - The host is paused and runs no kernel
   * - Device model
     - ``qemu-device`` adapter
     - ``-machine x-remote,vfio-user=on,auto-shutdown=off``
   * - Device export
     - ``x-vfio-user-server`` object
     - Exports the PCI device described by ``args.device`` on a Unix socket
   * - Build dependency
     - QEMU with vfio-user support
     - Built by ``just build-qemu``
   * - Readiness probes
     - Optional ``ready_log``, socket existence, QMP negotiation
     - Order defined by the adapter contract

Running this machine
--------------------

.. code-block:: bash

   # Build QEMU with vfio-user support first
   just build-qemu
   # Validate and preview
   just run-cli validate samples/machines/qemu-device.yaml --assets
   just run-cli plan samples/machines/qemu-device.yaml
   # Smoke run for two seconds
   just run-topology-dev samples/machines/qemu-device.yaml --run-for 2

- The device process starts first and begins listening; the host starts only after the device is ready.
- On shutdown the host stops first, and the device exits after its last lease is released.
- The vfio-user interface details are in :ref:`arch-vfio-user` and the lifecycle in :ref:`launcher-session-lifecycle`.

Verification
------------

- The plan output is one host process and one device process, with the device starting before the host.
- The integration test ``vfio_user_devices_start_before_the_host_and_stop_after_it`` covers this start and stop order.
- The integration test ``vfio_user_option_rom_is_checked_and_exposed`` covers a missing option ROM, an unreadable one, and exposure through the ROM BAR.
- Both tests run through ``just test-cosim-vfio-user`` with artifacts from ``just build-qemu``.

Limitations
-----------

- The host is paused and there is no guest; the guest device-driver path is outside this board.
- ``edu`` is a test device with no matching guest driver.
- ``qemu-device`` rejects ``config`` and private memory regions; the launch contract is fixed by the adapter.
- Running needs the locally built QEMU; a system QEMU is not guaranteed to include vfio-user support. Running a session needs Linux glibc and ``setpriv``.

Related pages
-------------

- Device catalog: :doc:`../devices/index`
- Host profiles: :doc:`../hosts/index`
- Machine catalog: :doc:`index`
- Chapter 4: :ref:`sim-qemu-device-models`, :ref:`sim-qemu-vhost`
- Adapter contract: :ref:`ref-device-adapters`
- Sources: ``samples/machines/qemu-device.yaml``, ``samples/devices/pci/qemu-edu.yaml``
