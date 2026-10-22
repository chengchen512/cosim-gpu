.. SPDX-License-Identifier: Apache-2.0

.. _ref-gart-format:

GART 格式
=========

本页是 GART 表项格式、aperture 寄存器编码与协同仿真典型布局的唯一事实源。地址空间分类与翻译流程的叙述见 :ref:`sim-gem5-address-translation`，本页只保留格式与数值。

PTE 格式
--------

每个 GART 页表项为 8 字节：

.. list-table::
   :header-rows: 1

   * - 位域
     - 字段
     - 描述
   * - 0
     - Valid
     - 表项有效
   * - 1
     - System
     - 1 表示系统内存，0 表示本地 VRAM
   * - 5:2
     - Fragment
     - 页面片段大小
   * - 47:12
     - Physical Page
     - 物理地址右移 12 位
   * - 51:48
     - Block Fragment
     - 块片段大小
   * - 63:52
     - Flags
     - MTYPE、PRT 等标志

物理地址提取方式为 ``paddr = (bits(PTE, 47, 12) << 12) | page_offset``。页表项内的偏移由相对于 GART aperture 的页索引计算。

aperture 寄存器
---------------

驱动通过 MMIO 写入以下寄存器，gem5 在 ``vmContext0`` 中保存对应状态：

.. list-table::
   :header-rows: 1

   * - 寄存器
     - gem5 字段
     - 编码
     - 含义
   * - ``MC_VM_FB_LOCATION_BASE``
     - ``vmContext0.fbBase``
     - ``bits[23:0] << 24``
     - VRAM 在 MC 地址空间中的起始地址
   * - ``MC_VM_FB_LOCATION_TOP``
     - ``vmContext0.fbTop``
     - ``bits[23:0] << 24 | 0xFFFFFF``
     - VRAM 结束地址
   * - ``MC_VM_FB_OFFSET``
     - ``vmContext0.fbOffset``
     - ``bits[23:0] << 24``
     - FB 重定位偏移
   * - ``MC_VM_AGP_BASE``
     - ``vmContext0.agpBase``
     - ``bits[23:0] << 24``
     - AGP 重映射基地址
   * - ``MC_VM_AGP_BOT``
     - ``vmContext0.agpBot``
     - ``bits[23:0] << 24``
     - AGP aperture 底部
   * - ``MC_VM_AGP_TOP``
     - ``vmContext0.agpTop``
     - ``bits[23:0] << 24 | 0xFFFFFF``
     - AGP aperture 顶部
   * - ``MC_VM_SYSTEM_APERTURE_LOW_ADDR``
     - ``vmContext0.sysAddrL``
     - ``bits[29:0] << 18``
     - system aperture 低地址
   * - ``MC_VM_SYSTEM_APERTURE_HIGH_ADDR``
     - ``vmContext0.sysAddrH``
     - ``bits[29:0] << 18``
     - system aperture 高地址
   * - ``VM_CONTEXT0_PAGE_TABLE_BASE_ADDR``
     - ``vmContext0.ptBase``
     - raw 64-bit
     - GART 表在 VRAM 中的位置
   * - ``VM_CONTEXT0_PAGE_TABLE_START_ADDR``
     - ``vmContext0.ptStart``
     - raw 64-bit
     - GART aperture 起始页号
   * - ``VM_CONTEXT0_PAGE_TABLE_END_ADDR``
     - ``vmContext0.ptEnd``
     - raw 64-bit
     - GART aperture 结束页号

协同仿真典型值
--------------

cosim 运行时的典型寄存器取值：

.. code-block:: text

   ptBase   = 0x3EE600000     GART table at VRAM offset ~15.7 GiB
   ptStart  = 0x7FFF00000     GART covers GPU VAs from 0x7FFF00000000
   ptEnd    = 0x7FFF1FFFF     GART covers ~128K pages (512 MiB)
   fbBase   = 0x8000000000    VRAM starts at MC address 512 GiB
   fbTop    = 0x8400FFFFFF    VRAM ends at ~528 GiB (16 GiB range)
   sysAddrL = 0x0             System aperture start
   sysAddrH = 0x3FFEC0000     System aperture end (~4 TiB)

GART 表在 VRAM 中的布局
-----------------------

GART 表从 ``ptBase`` 开始连续存放，第 N 项映射 ``ptStart + N`` 页：

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

协同仿真回退查找
----------------

cosim 下 VRAM 由共享内存支撑，驱动的 VRAM 写入绕过 gem5，``AMDGPUVM::gartTable`` 不会被填充。翻译路径因此直接从共享 VRAM 读取 PTE：

.. code-block:: cpp

   Addr pte_table_offset = gart_addr - (ptStart * 8);
   Addr pte_vram_offset = gartBase() + pte_table_offset;
   memcpy(&pte, vramShmemPtr + pte_vram_offset, sizeof(pte));

- ``getGARTAddr()`` 已经把页索引乘以 8，得到的地址本身就是字节偏移；回退路径不能再乘 8。

- PTE 为 0 表示未映射，此时把地址映射到 sink（``paddr=0``）：读返回零、写被丢弃，仿真继续运行。

- 回退只影响 gem5 侧的地址翻译，不改变客户机驱动看到的 GART 表内容。

来源与维护
----------

格式定义与实现：

- ``third_party/gem5/src/dev/amdgpu/amdgpu_vm.{cc,hh}``：翻译生成器、``vmContext0`` 寄存器状态与共享 VRAM 回退。

- ``third_party/gem5/src/dev/amdgpu/amdgpu_device.cc``：通过共享客户机内存读取 ROM 与 IH 记录。

- 典型值来自 cosim 配置的实际运行输出，只作对照，不作为接口约定；报告问题时应附上当时的寄存器值与 PTE。

核对命令：

.. code-block:: bash

   just run-launch --gem5-debug AMDGPUDevice,PM4PacketProcessor
   build/gem5/x86_64/VEGA_X86/gem5.opt --debug-flags=AMDGPUDevice --help

相关页面
--------

- GPU 地址翻译流程：:ref:`sim-gem5-address-translation`

- gem5 MI300X 模型：:ref:`sim-gem5-model`

- MI300X PCI/BAR 接口：:ref:`sim-gem5-pci`

- 相关已知问题：:doc:`known_issues`

- 模型调试：:ref:`sim-debugging-models`
