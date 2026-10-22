.. SPDX-License-Identifier: Apache-2.0

.. _sim-gem5-address-translation:

GPU address translation
========================

This page describes how ``AMDGPUVM`` translates GPU access addresses in gem5 and how co-simulation falls back to shared VRAM for GART page tables when VRAM writes bypass gem5. The complete PTE and aperture reference is :ref:`ref-gart-format`.

Address Classes and Translation
--------------------------------

.. list-table::
   :header-rows: 1

   * - Address class
     - Translation
   * - AGP
     - ``physical = virtual - agpBot + agpBase``.
   * - VMID 0 GART
     - Single-level GPU page table: the PTE yields the physical page number and the page offset is appended.
   * - Framebuffer
     - Device-relative VRAM offset.
   * - MMHUB
     - Offset in the VRAM address window, mirroring the framebuffer.
   * - VMID greater than zero
     - Context-specific multi-level page-table walk by ``VegaISA::Walker``, including the TLB invalidation handling of the model.

``AMDGPUVM`` provides four translators: ``AGPTranslationGen``, ``GARTTranslationGen``, ``MMHUBTranslationGen`` and ``UserTranslationGen``. The driver programs aperture registers and page-table bases through MMIO.

Register State
---------------

.. list-table::
   :header-rows: 1

   * - Register
     - gem5 field
     - Purpose
   * - ``MC_VM_FB_LOCATION_BASE`` and ``TOP``
     - ``fbBase``, ``fbTop``
     - Start and end of VRAM in the MC address space.
   * - ``MC_VM_FB_OFFSET``
     - ``fbOffset``
     - Framebuffer relocation offset.
   * - ``MC_VM_AGP_BASE``, ``BOT`` and ``TOP``
     - ``agpBase``, ``agpBot``, ``agpTop``
     - AGP aperture remapping and bounds.
   * - ``MC_VM_SYSTEM_APERTURE_*``
     - ``sysAddrL``, ``sysAddrH``
     - Start and end of the system memory aperture.
   * - ``VM_CONTEXT0_PAGE_TABLE_*``
     - ``ptBase``, ``ptStart``, ``ptEnd``
     - Location of the GART table in VRAM and the page-number range of the aperture.

GART Table and PTEs
--------------------

- Each GART page-table entry occupies eight bytes; the page index within the aperture determines the table offset.
- A valid PTE yields the physical address as ``paddr = (bits(PTE, 47, 12) << 12) | page_offset``.
- A zero PTE means the page is unmapped. In co-simulation unmapped pages map to a sink instead of producing a page fault.
- PM4 and SDMA call ``getGARTAddr()`` where an encoded page-table address is required; it already multiplies the page number by eight.

Shared VRAM Fallback in Co-simulation
--------------------------------------

QEMU maps the VRAM BAR directly through a ``memory-backend-file`` with ``share=on``. Driver writes to VRAM bypass the gem5 memory system, so ``gartTable``, which would be populated by intercepting VRAM writes, stays empty in co-simulation. ``GARTTranslationGen::translate()`` reads the PTE directly from shared VRAM when the table lookup misses:

.. code-block:: cpp

   Addr gart_start_addr = ptStart * 8;
   Addr pte_table_offset = gart_addr - gart_start_addr;
   // First interpret ptBase as a raw VRAM byte offset
   Addr pte_vram_offset = gartBase() + pte_table_offset;
   memcpy(&pte, vramShmemPtr + pte_vram_offset, sizeof(pte));
   // If the PTE is still zero, try the fbBase-relative interpretation
   Addr adj = gartBase() - fbBase;
   memcpy(&pte, vramShmemPtr + adj + pte_table_offset, sizeof(pte));

- ``getGARTAddr()`` already multiplies the page index by eight, so ``bits(vaddr, 63, 12)`` is the table byte offset and must not be multiplied again.
- The first fallback lookup emits a one-shot diagnostic with ``ptBase``, ``ptStart``, ``fbBase`` and the first eight PTEs; the first successful translation also logs a warning.
- A valid PTE yields the physical address from its bit fields. A zero PTE maps to the sink: reads return zero, writes are discarded and the simulation continues. This is expected because the first page at ``ptStart`` is itself unmapped.
- Only when no shared VRAM mapping exists does the code fall back to ``GenericPageTableFault``.

Three Layers of VRAM Address Protection
----------------------------------------

- PM4: ``writeData``, ``releaseMem`` and ``queryStatus`` test the destination with ``isVRAMAddress()`` and route it to the GPU memory manager instead of translating a VRAM address as a system address.
- SDMA: paths such as the rptr writeback skip ``getGARTAddr()`` for VRAM addresses.
- GART fallback: when the reverse-decoded address still falls in VRAM, it maps to the sink and the warning states that VRAM write-backs are no-ops.

Page Table Updates
-------------------

- The guest updates page tables through the QEMU-mapped VRAM BAR, so writes land directly in shared VRAM.
- The gem5 translation path reads shared VRAM and handles page-table bases expressed relative to the framebuffer.
- User-context walks use ``VegaISA::Walker`` together with the TLB invalidation handling of the model; the runtime only preserves mapping offsets and sizes.
- Address classification and page-fault handling stay inside the GPU model; the launcher takes no part in translation.

Sources
--------

- Translators and fallback: ``third_party/gem5/src/dev/amdgpu/amdgpu_vm.cc`` and ``amdgpu_vm.hh``.
- VRAM address test: ``isVRAMAddress()`` in ``third_party/gem5/src/dev/amdgpu/pm4_packet_processor.cc``.
- Shared VRAM mapping: ``PhysicalMemory`` in ``third_party/gem5/src/mem/physical.cc``.
- PTE bit fields and typical values: :ref:`ref-gart-format`.

Related Pages
--------------

- :doc:`mi300x_model` for the model structure and command paths.
- :doc:`mi300x_pci` for how the VRAM BAR maps the shared file.
- :doc:`../debugging_models` for reading GART-related warnings.
- :ref:`ref-gart-format` for PTEs, aperture registers and typical values.
- :ref:`arch-memory-model` for shared memory and guest physical address layout.
