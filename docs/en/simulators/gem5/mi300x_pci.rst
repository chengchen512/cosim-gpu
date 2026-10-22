.. SPDX-License-Identifier: Apache-2.0

.. _sim-gem5-pci:

MI300X PCI interface
=====================

This page describes how the gem5 MI300X device model appears to the host QEMU: PCI identity, configuration space, BAR layout, MSI-X interrupts and the option ROM. These details decide whether the ``amdgpu`` driver discovers the device correctly.

Identity and Configuration Space
---------------------------------

.. list-table::
   :header-rows: 1

   * - Field
     - Value
     - Notes
   * - Vendor ID
     - ``0x1002``
     - AMD.
   * - Device ID
     - ``0x74a0``
     - MI300X.
   * - Subsystem
     - ``0x1002:0x74a0``
     - Same as the main IDs.
   * - Class code
     - ``0x030000``
     - ``PCI_CLASS_DISPLAY_VGA``, which makes the driver check the legacy VGA ROM.
   * - Configuration space
     - 4096 bytes
     - PCIe extended configuration space.
   * - PCIe capability
     - Version 2
     - Endpoint, 512-byte maximum payload, FLR capable.

Standard PCI header fields are handled by libvfio-user, and non-standard writes are forwarded to ``AMDGPUDevice`` through the configuration-space callback. A vfio-user reset callback reinitializes model state.

BAR Layout
-----------

.. list-table::
   :header-rows: 1

   * - BAR
     - Contents
     - Size and type
     - Access path
   * - 0 + 1
     - VRAM
     - VRAM size from the memory layout (power of two, 16 GiB by default), 64-bit prefetchable
     - Zero-copy mmap of the shared file descriptor; BAR callback when mmap is unavailable
   * - 2 + 3
     - Doorbell
     - 2 MiB, 64-bit non-prefetchable
     - vfio-user BAR callback forwarded to doorbell handling
   * - 4
     - MSI-X table and PBA
     - 8 KiB region, 256 vectors
     - libvfio-user handles table and PBA accesses internally
   * - 5
     - MMIO registers
     - 512 KiB, 32-bit
     - vfio-user BAR callback forwarded to ``AMDGPUDevice`` register handling

- The upper halves of the 64-bit BARs (BAR1 and BAR3) do not register separate regions and must read as zero during size probing.
- After initialization the model fixes the BAR type bits: BAR0 is 64-bit prefetchable and BAR2 is 64-bit non-prefetchable, so the upper halves are not mistaken for I/O BARs.
- The driver accesses VRAM at BAR0, doorbells at BAR2 and MMIO at BAR5.
- The expansion ROM BAR reports a size of ``0x1000`` during probing. The legacy VGA ROM window lives at ``0xC0000`` and is decoded only by GPU 0.

Interrupts
-----------

- The MSI-X capability is registered in BAR4: the table is at offset 0, the PBA follows the table, and there are 256 vectors.
- One INTx vector is registered as a fallback.
- When ``AMDGPUDevice::intrPost()`` requests an interrupt, it calls ``MI300XVfioUser``, which triggers the configured IRQ eventfd. With KVM, the registered eventfd can inject interrupts into the guest.
- The interrupt record itself is written first to the IH ring in shared guest memory; the guest reads the record and handles the completion values.

Option ROM
-----------

- The host template passes ``pci.rom`` as the vfio-user client ``romfile``, so its bytes are exposed to the guest through the ROM BAR. The launcher checks that the file exists before allocating session resources.
- The MI300X template points at ``third_party/gem5-resources/src/x86-ubuntu-gpu-ml/files/mi300.rom``, and each device may override the path.
- Before ``modprobe``, the guest runs ``dd if=/root/roms/mi300.rom of=/dev/mem bs=1k seek=768 count=128``, which writes the 128 KiB ROM at physical addresses ``0xC0000`` to ``0xDFFFF``.
- ``AMDGPUDevice::readROM()`` reads shared guest memory at ``VGA_ROM_DEFAULT + offset``. With multiple GPUs the ROM contents are read through system memory.
- The explicit write is required because all five amdgpu BIOS discovery paths fail in co-simulation; see :doc:`../guest_driver`.

Sources
--------

- vfio-user server: ``third_party/gem5/src/dev/amdgpu/mi300x_vfio_user.cc`` and ``mi300x_vfio_user.hh``.
- Device model: ``third_party/gem5/src/dev/amdgpu/amdgpu_device.cc`` and ``amdgpu_defines.hh``.
- SimObject wrapper: ``third_party/gem5/src/dev/amdgpu/MI300XVfioUser.py``.
- ROM and VGA window constants: ``VGA_ROM_DEFAULT = 0xC0000`` and ``ROM_SIZE = 0x20000``.

Related Pages
--------------

- :doc:`mi300x_model` for the command, DMA and interrupt paths.
- :doc:`address_translation` for GPU address translation.
- :doc:`../guest_driver` for guest driver requirements and the ROM write.
- :ref:`arch-vfio-user` for the vfio-user interface.
- :ref:`ref-device-adapters` for the MI300X template PCI constraints.
