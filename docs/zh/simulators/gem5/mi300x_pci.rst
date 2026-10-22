.. SPDX-License-Identifier: Apache-2.0

.. _sim-gem5-pci:

MI300X PCI/BAR 接口
====================

本页说明 gem5 的 MI300X 设备模型如何呈现给 host QEMU：PCI 身份、配置空间、BAR 布局、MSI-X 中断和 option ROM。这些细节决定 ``amdgpu``\ 驱动能否正确探测设备。

身份与配置空间
---------------

.. list-table::
   :header-rows: 1

   * - 字段
     - 值
     - 说明
   * - Vendor ID
     - ``0x1002``
     - AMD。
   * - Device ID
     - ``0x74a0``
     - MI300X。
   * - Subsystem
     - ``0x1002:0x74a0``
     - 与主 ID 相同。
   * - Class code
     - ``0x030000``
     - ``PCI_CLASS_DISPLAY_VGA``\ ，驱动据此检查传统 VGA ROM。
   * - 配置空间
     - 4096 字节
     - PCIe 扩展配置空间。
   * - PCIe capability
     - 版本 2
     - Endpoint、最大负载 512 字节、具备 FLR 能力。

标准 PCI 头字段由 libvfio-user 处理，非标准写由设备的配置空间回调转发给 ``AMDGPUDevice``\ 。设备 reset 通过 vfio-user reset 回调重新初始化模型状态。

BAR 布局
---------

.. list-table::
   :header-rows: 1

   * - BAR
     - 内容
     - 大小与类型
     - 访问路径
   * - 0 + 1
     - VRAM
     - 内存布局中的 VRAM 大小（2 的幂，默认 16 GiB），64 位可预取
     - 共享文件描述符 mmap 零拷贝；不可 mmap 时回落 BAR 回调
   * - 2 + 3
     - Doorbell
     - 2 MiB，64 位非可预取
     - vfio-user BAR 回调，转发到门铃处理
   * - 4
     - MSI-X 表与 PBA
     - 8 KiB 区域，256 个向量
     - libvfio-user 内部处理表与 PBA 访问
   * - 5
     - MMIO 寄存器
     - 512 KiB，32 位
     - vfio-user BAR 回调，转发到 ``AMDGPUDevice``\ 的寄存器处理

- 64 位 BAR 的高半部分（BAR1、BAR3）不注册独立区域，大小探测时高半部分必须为零。
- 初始化完成后模型会修正 BAR 类型位：BAR0 为 64 位可预取，BAR2 为 64 位非可预取，避免把高半部分误标为 I/O BAR。
- 驱动按约定访问：VRAM 在 BAR0，门铃在 BAR2，MMIO 在 BAR5。
- 扩展 ROM BAR 的大小探测返回 ``0x1000``\ ；旧式 VGA ROM 窗口位于 ``0xC0000``\ ，且只有 GPU 0 解码该窗口。

中断
-----

- MSI-X capability 注册在 BAR4：表位于偏移 0，PBA 紧跟表之后，共 256 个向量。
- 同时注册 1 个 INTx 向量作为回退。
- ``AMDGPUDevice::intrPost()``\ 请求中断时调用 ``MI300XVfioUser``\ ，再触发配置的 IRQ eventfd；使用 KVM 时该 eventfd 可向客户机注入中断。
- 中断记录本身先写入共享客户机内存的 IH ring，客户机读取记录并处理完成标记。

Option ROM
-----------

- host 模板把 ``pci.rom``\ 作为 vfio-user 客户端的 ``romfile``\ ，其内容通过该设备的 ROM BAR 呈现给客户机；launcher 在分配会话资源前检查文件存在。
- MI300X 模板指向 ``third_party/gem5-resources/src/x86-ubuntu-gpu-ml/files/mi300.rom``\ ，各设备可以覆盖这个路径。
- 客户机在 ``modprobe``\ 之前执行 ``dd if=/root/roms/mi300.rom of=/dev/mem bs=1k seek=768 count=128``\ ，把 128 KiB ROM 写到物理地址 ``0xC0000``\ 至 ``0xDFFFF``\ 。
- gem5 的 ``AMDGPUDevice::readROM()``\ 从 ``VGA_ROM_DEFAULT + offset``\ 读取共享客户机内存；多 GPU 时 ROM 内容通过系统内存读取。
- 之所以必须显式写入，是因为 amdgpu 的五种 BIOS 发现路径在协同仿真下全部失败，详见 :doc:`../guest_driver`\ 。

源码与依据
-----------

- vfio-user 服务端：``third_party/gem5/src/dev/amdgpu/mi300x_vfio_user.cc``\ 、``mi300x_vfio_user.hh``\ 。
- 设备模型：``third_party/gem5/src/dev/amdgpu/amdgpu_device.cc``\ 、``amdgpu_defines.hh``\ 。
- SimObject 封装：``third_party/gem5/src/dev/amdgpu/MI300XVfioUser.py``\ 。
- ROM 与 VGA 窗口常量：``VGA_ROM_DEFAULT = 0xC0000``\ 、``ROM_SIZE = 0x20000``\ 。

相关页面
---------

- :doc:`mi300x_model`\ ：命令、DMA 与中断路径。
- :doc:`address_translation`\ ：GPU 地址翻译。
- :doc:`../guest_driver`\ ：客户机驱动要求与 ROM 写入。
- :ref:`arch-vfio-user`\ ：vfio-user 通信接口。
- :ref:`ref-device-adapters`\ ：MI300X 模板的 PCI 元数据约束。
