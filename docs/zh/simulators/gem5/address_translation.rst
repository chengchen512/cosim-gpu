.. SPDX-License-Identifier: Apache-2.0

.. _sim-gem5-address-translation:

GPU 地址翻译
=============

本页说明 gem5 的 ``AMDGPUVM``\ 如何翻译 GPU 访问地址，以及协同仿真中 VRAM 写入绕过 gem5 时如何从共享 VRAM 回退读取 GART 页表。PTE 位域与 aperture 寄存器的完整表格见 :ref:`ref-gart-format`\ 。

地址类别与翻译方式
-------------------

.. list-table::
   :header-rows: 1

   * - 地址类别
     - 翻译方式
   * - AGP
     - ``physical = virtual - agpBot + agpBase``\ 。
   * - VMID 0 GART
     - 单级 GPU 页表：PTE 给出物理页号，再拼接页内偏移。
   * - Framebuffer
     - 设备内部 VRAM 偏移。
   * - MMHUB
     - VRAM 地址窗口偏移，镜像 framebuffer。
   * - VMID 大于零
     - 当前上下文的多级页表遍历，由 ``VegaISA::Walker``\ 完成，并处理模型中的 TLB 失效。

``AMDGPUVM``\ 提供 ``AGPTranslationGen``\ 、``GARTTranslationGen``\ 、``MMHUBTranslationGen``\ 和 ``UserTranslationGen``\ 四个翻译器。驱动通过 MMIO 设置地址窗口寄存器和页表基址。

寄存器状态
-----------

.. list-table::
   :header-rows: 1

   * - 寄存器
     - gem5 字段
     - 作用
   * - ``MC_VM_FB_LOCATION_BASE``\ / ``TOP``
     - ``fbBase``\ 、``fbTop``
     - VRAM 在 MC 地址空间中的起止地址。
   * - ``MC_VM_FB_OFFSET``
     - ``fbOffset``
     - framebuffer 重定位偏移。
   * - ``MC_VM_AGP_BASE``\ / ``BOT``\ / ``TOP``
     - ``agpBase``\ 、``agpBot``\ 、``agpTop``
     - AGP aperture 的重映射与边界。
   * - ``MC_VM_SYSTEM_APERTURE_*``
     - ``sysAddrL``\ 、``sysAddrH``
     - 系统内存 aperture 的起止地址。
   * - ``VM_CONTEXT0_PAGE_TABLE_*``
     - ``ptBase``\ 、``ptStart``\ 、``ptEnd``
     - GART 表在 VRAM 中的位置和 aperture 的页号范围。

GART 表与 PTE
--------------

- 每个 GART 页表项占 8 字节；aperture 内的页索引决定表内偏移。
- 有效 PTE 的物理地址按 ``paddr = (bits(PTE, 47, 12) << 12) | page_offset``\ 计算。
- PTE 为 0 表示该页未映射；未映射页在协同仿真中按 sink 处理，而不是产生页错误。
- PM4 和 SDMA 在需要编码后的页表地址时调用 ``getGARTAddr()``\ ，该函数已把页号乘以 8。

协同仿真中的共享 VRAM 回退
---------------------------

QEMU 通过 ``share=on``\ 的 ``memory-backend-file``\ 直接映射 VRAM BAR。驱动对 VRAM 的写入完全绕过 gem5 的内存系统，因此依赖“拦截 VRAM 写入”填充的 ``gartTable``\ 在协同仿真中为空。``GARTTranslationGen::translate()``\ 在表项未命中时直接从共享 VRAM 读取 PTE：

.. code-block:: cpp

   Addr gart_start_addr = ptStart * 8;
   Addr pte_table_offset = gart_addr - gart_start_addr;
   // 先按 ptBase 是 VRAM 字节偏移解释
   Addr pte_vram_offset = gartBase() + pte_table_offset;
   memcpy(&pte, vramShmemPtr + pte_vram_offset, sizeof(pte));
   // PTE 仍为 0 时再尝试 ptBase 相对 fbBase 的解释
   Addr adj = gartBase() - fbBase;
   memcpy(&pte, vramShmemPtr + adj + pte_table_offset, sizeof(pte));

- ``getGARTAddr()``\ 已经把页索引乘以 8，因此 ``bits(vaddr, 63, 12)``\ 本身就是表内字节偏移，不能再乘一次 8。
- 第一次回退查询会输出一次性诊断，打印 ``ptBase``\ 、``ptStart``\ 、``fbBase``\ 等寄存器和表头前 8 个 PTE；第一次成功翻译也会打一条警告。
- PTE 有效时按位域拼接物理地址；PTE 为 0 时按 sink 处理，读返回 0、写被丢弃，仿真继续运行。这是正常现象：``ptStart``\ 处的第一页本身就是未映射的。
- 若没有共享 VRAM 映射，才回退到 ``GenericPageTableFault``\ 。

VRAM 地址的三层防护
--------------------

- PM4：``writeData``\ 、``releaseMem``\ 和 ``queryStatus``\ 先用 ``isVRAMAddress()``\ 判断目标，再路由到 GPU 内存管理器，避免把 VRAM 地址当成系统地址做 GART 翻译。
- SDMA：rptr 回写等路径对 VRAM 地址跳过 ``getGARTAddr()``\ 。
- GART 兜底：地址在取反编码后仍落在 VRAM 范围内时映射到 sink，并在警告中说明“VRAM 回写是空操作”。

页表更新
---------

- 客户机通过 QEMU 映射的 VRAM BAR 更新页表，写入直接落到共享 VRAM。
- gem5 的翻译路径读取共享 VRAM，并处理以 framebuffer 为基准的页表基址差异。
- 用户上下文遍历使用 ``VegaISA::Walker``\ ，配合模型中的 TLB 失效处理；运行管理程序只提供正确的映射偏移与大小。
- 地址分类和页错误处理留在 GPU 模型内，launcher 不参与翻译。

源码与依据
-----------

- 翻译器与回退：``third_party/gem5/src/dev/amdgpu/amdgpu_vm.cc``\ 、``amdgpu_vm.hh``\ 。
- VRAM 地址判断：``third_party/gem5/src/dev/amdgpu/pm4_packet_processor.cc``\ 中的 ``isVRAMAddress()``\ 。
- 共享 VRAM 映射：``third_party/gem5/src/mem/physical.cc``\ 的 ``PhysicalMemory``\ 。
- PTE 位域与典型值：:ref:`ref-gart-format`\ 。

相关页面
---------

- :doc:`mi300x_model`\ ：模型整体结构与命令路径。
- :doc:`mi300x_pci`\ ：VRAM BAR 如何映射共享文件。
- :doc:`../debugging_models`\ ：如何解读 GART 相关警告。
- :ref:`ref-gart-format`\ ：PTE、aperture 寄存器与典型值。
- :ref:`arch-memory-model`\ ：共享内存与客户机物理地址布局。
