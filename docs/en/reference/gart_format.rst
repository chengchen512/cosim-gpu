.. SPDX-License-Identifier: Apache-2.0

.. _ref-gart-format:

GART format
===========

This page is the single source of truth for GART entry format, aperture register encoding and the typical co-simulation layout. Address space classes and the translation flow are explained in :ref:`sim-gem5-address-translation`; this page keeps formats and values only.

PTE format
----------

Each GART page table entry is 8 bytes:

.. list-table::
   :header-rows: 1

   * - Bits
     - Field
     - Description
   * - 0
     - Valid
     - entry is valid
   * - 1
     - System
     - 1 for system memory, 0 for local VRAM
   * - 5:2
     - Fragment
     - page fragment size
   * - 47:12
     - Physical Page
     - physical address shifted right by 12
   * - 51:48
     - Block Fragment
     - block fragment size
   * - 63:52
     - Flags
     - MTYPE, PRT and related flags

The physical address is extracted as ``paddr = (bits(PTE, 47, 12) << 12) | page_offset``. The offset inside the table is computed from the page index relative to the GART aperture.

Aperture registers
------------------

The driver writes the following registers through MMIO and gem5 keeps the corresponding state in ``vmContext0``:

.. list-table::
   :header-rows: 1

   * - Register
     - gem5 field
     - Encoding
     - Meaning
   * - ``MC_VM_FB_LOCATION_BASE``
     - ``vmContext0.fbBase``
     - ``bits[23:0] << 24``
     - start of VRAM in MC address space
   * - ``MC_VM_FB_LOCATION_TOP``
     - ``vmContext0.fbTop``
     - ``bits[23:0] << 24 | 0xFFFFFF``
     - end of VRAM
   * - ``MC_VM_FB_OFFSET``
     - ``vmContext0.fbOffset``
     - ``bits[23:0] << 24``
     - FB relocation offset
   * - ``MC_VM_AGP_BASE``
     - ``vmContext0.agpBase``
     - ``bits[23:0] << 24``
     - AGP remap base address
   * - ``MC_VM_AGP_BOT``
     - ``vmContext0.agpBot``
     - ``bits[23:0] << 24``
     - AGP aperture bottom
   * - ``MC_VM_AGP_TOP``
     - ``vmContext0.agpTop``
     - ``bits[23:0] << 24 | 0xFFFFFF``
     - AGP aperture top
   * - ``MC_VM_SYSTEM_APERTURE_LOW_ADDR``
     - ``vmContext0.sysAddrL``
     - ``bits[29:0] << 18``
     - system aperture low address
   * - ``MC_VM_SYSTEM_APERTURE_HIGH_ADDR``
     - ``vmContext0.sysAddrH``
     - ``bits[29:0] << 18``
     - system aperture high address
   * - ``VM_CONTEXT0_PAGE_TABLE_BASE_ADDR``
     - ``vmContext0.ptBase``
     - raw 64-bit
     - location of the GART table in VRAM
   * - ``VM_CONTEXT0_PAGE_TABLE_START_ADDR``
     - ``vmContext0.ptStart``
     - raw 64-bit
     - GART aperture start page number
   * - ``VM_CONTEXT0_PAGE_TABLE_END_ADDR``
     - ``vmContext0.ptEnd``
     - raw 64-bit
     - GART aperture end page number

Typical values under co-simulation
----------------------------------

Typical register values during a cosim run:

.. code-block:: text

   ptBase   = 0x3EE600000     GART table at VRAM offset ~15.7 GiB
   ptStart  = 0x7FFF00000     GART covers GPU VAs from 0x7FFF00000000
   ptEnd    = 0x7FFF1FFFF     GART covers ~128K pages (512 MiB)
   fbBase   = 0x8000000000    VRAM starts at MC address 512 GiB
   fbTop    = 0x8400FFFFFF    VRAM ends at ~528 GiB (16 GiB range)
   sysAddrL = 0x0             System aperture start
   sysAddrH = 0x3FFEC0000     System aperture end (~4 TiB)

GART table layout in VRAM
-------------------------

The GART table is stored contiguously from ``ptBase``; entry N maps page ``ptStart + N``:

.. code-block:: text

   VRAM offset = ptBase (gartBase)
   +-------------------+  ptBase + 0
   | PTE[0]  (8 bytes) |  maps page ptStart
   +-------------------+  ptBase + 8
   | PTE[1]            |  maps page ptStart + 1
   +-------------------+  ptBase + 16
   | PTE[2]            |  maps page ptStart + 2
   | ...               |
   +-------------------+
   | PTE[N]            |  maps page ptStart + N
   +-------------------+  ptBase + (ptEnd - ptStart + 1) * 8

Co-simulation fallback lookup
-----------------------------

Under cosim, VRAM is backed by shared memory and driver writes bypass gem5, so ``AMDGPUVM::gartTable`` is never populated. The translation path therefore reads PTEs directly from shared VRAM:

.. code-block:: cpp

   Addr pte_table_offset = gart_addr - (ptStart * 8);
   Addr pte_vram_offset = gartBase() + pte_table_offset;
   memcpy(&pte, vramShmemPtr + pte_vram_offset, sizeof(pte));

- ``getGARTAddr()`` already multiplies the page index by 8, so the resulting address is a byte offset; the fallback must not multiply by 8 again.

- A zero PTE means unmapped: the address is mapped to a sink (``paddr=0``), reads return zero, writes are discarded and the simulation keeps running.

- The fallback only affects gem5-side translation; the guest driver still sees the GART table it wrote.

Sources and maintenance
-----------------------

Format definitions and implementation:

- ``third_party/gem5/src/dev/amdgpu/amdgpu_vm.{cc,hh}``: translation generators, ``vmContext0`` register state and the shared-VRAM fallback.

- ``third_party/gem5/src/dev/amdgpu/amdgpu_device.cc``: ROM and IH record access through shared guest memory.

- The typical values come from real cosim runs and are for comparison only, not an interface contract; include the register values and PTE when reporting an issue.

Verification commands:

.. code-block:: bash

   just run-launch --gem5-debug AMDGPUDevice,PM4PacketProcessor
   build/gem5/x86_64/VEGA_X86/gem5.opt --debug-flags=AMDGPUDevice --help

Related pages
-------------

- GPU address translation flow: :ref:`sim-gem5-address-translation`

- gem5 MI300X model: :ref:`sim-gem5-model`

- MI300X PCI/BAR interface: :ref:`sim-gem5-pci`

- Related known issues: :doc:`known_issues`

- Model debugging: :ref:`sim-debugging-models`
