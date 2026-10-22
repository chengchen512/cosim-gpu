.. SPDX-License-Identifier: Apache-2.0

.. _sim-index:

QEMU and gem5
==============

This chapter introduces the two simulators of the co-simulation: QEMU provides the guest runtime and functional device models, and gem5 provides performance simulation of the MI300X.

Functional and Performance Simulation
--------------------------------------

As the vhost, QEMU runs guest Linux, the amdgpu driver and ROCm applications and provides the CPU, memory and PCIe environment. It can also act as a device model process that exports a PCI device over vfio-user, guaranteeing functional correctness without microarchitectural timing. gem5 models the MI300X command processors, execution units, caches and memory hierarchy and provides the timing behavior relevant to performance.

.. list-table::
   :header-rows: 1

   * - Simulator
     - Role
     - Focus
   * - QEMU (vhost)
     - Guest runtime
     - CPU, memory, PCIe, boot, QMP and serial
   * - QEMU (device model)
     - Functional PCI device model
     - Configuration space, BARs and interrupts
   * - gem5
     - MI300X performance model
     - PM4/SDMA, IH, GPU VM, shader/CU arrays and the Ruby memory hierarchy

Choosing a Device Implementation
---------------------------------

A topology chooses the device implementation through its device adapter: ``gem5-mi300x`` uses the gem5 MI300X performance model, ``qemu-device`` uses a QEMU functional device model, and the ``mixed-models`` machine uses both. Chapter 5 records the adapters of every machine, and the adapter contract lives in :ref:`ref-device-adapters`.

Chapter Contents
-----------------

.. toctree::
   :maxdepth: 1

   qemu/index
   gem5/index
   guest_driver
   debugging_models

Recommended Reading Path
-------------------------

- Start with this page and :doc:`qemu/index` and :doc:`gem5/index` for the division of labor.
- For guest startup, read :doc:`qemu/vhost`.
- For QEMU functional device models, read :doc:`qemu/device_models`.
- For the MI300X model, continue with :doc:`gem5/mi300x_pci` and the pages after it.
- For driver and model debugging, read :doc:`guest_driver` and :doc:`debugging_models`.
