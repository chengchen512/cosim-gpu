.. SPDX-License-Identifier: Apache-2.0


.. _topo-machines-single-gpu:

single-gpu 机器
===============

概述
----

``single-gpu`` 是标准单 GPU 客户机板卡：一台机器、一个 ``host-x86`` QEMU 主机和一个 gem5 MI300X 设备，共享一个 24 GiB 内存池。快速开始教程第一次会话使用的就是这个组合。

拓扑
----

.. code-block:: yaml

   # samples/machines/single-gpu.yaml
   version: 1
   imports:
     - hosts/qemu.yaml
     - devices/gpu/mi300x.yaml
   templates:
     node1:
       host: {use: host-x86}
       devices:
         - {use: mi300x}
   machines:
     - {id: m0, use: node1}

- 机器数量：1（``m0``\ ）；主机与设备都来自导入的模板。
- ``node1`` 把默认 ``host-x86`` 与默认 ``mi300x`` 组合起来；样例没有覆盖任何字段。
- 运行时可另外用 ``--payload`` 选择 ``ubuntu-rocm7_0``\ ，payload 不在拓扑文档中。

硬件资源
--------

.. list-table::
   :header-rows: 1

   * - 资源
     - 值
     - 来源
   * - 机器
     - 1 台（``m0``\ ）
     - ``samples/machines/single-gpu.yaml``
   * - 主机配置
     - ``host-x86``\ ：``q35``\ 、``kvm``\ 、``host`` CPU、4 vCPU
     - ``samples/hosts/qemu.yaml``
   * - 客户机 RAM
     - 8 GiB；x86_64 PCI 空洞由 ``memory_map`` 渲染
     - ``samples/hosts/qemu.yaml``
   * - 设备
     - 1 × ``mi300x``\ ：16 GiB VRAM、40 CU
     - ``samples/devices/gpu/mi300x.yaml``
   * - 内存池
     - 24 GiB = 8 GiB RAM + 16 GiB VRAM
     - ``crates/cosim-topology/src/layout.rs``
   * - PCIe 拓扑
     - 每个设备一个 ``pcie-root-port``\ （槽位从 ``0x10`` 起），可选 option ROM
     - ``samples/hosts/qemu.yaml``
   * - 可执行文件
     - QEMU ``build/qemu/qemu-system-x86_64``\ ；gem5 ``build/gem5/x86_64/VEGA_X86/gem5.opt``
     - 两个模板

软件栈
------

.. list-table::
   :header-rows: 1

   * - 层
     - 组件
     - 说明
   * - 客户机 OS
     - Ubuntu 24.04.2 LTS，内核 6.8.0-124-generic
     - 由 payload 直接内核启动
   * - GPU 驱动
     - ``amdgpu``\ ，固定参数
     - ``ip_block_mask=0x67 ppfeaturemask=0 dpm=0 audio=0 ras_enable=0 discovery=2``
   * - GPU 用户态
     - ROCm 7.0 / HIP
     - ``rocminfo``\ 、``rocm-smi`` 与 HIP 程序
   * - 设备模型
     - gem5 MI300X（``MI300XVfioUser``\ ）
     - PM4、SDMA、CU 等部分行为；模型细节见第 4 章
   * - 客户机初始化
     - ``cosim-gpu-setup.service``
     - 启动后执行 ROM ``dd`` 并加载 ``amdgpu``

运行该机器
----------

.. code-block:: bash

   # 只校验与预览
   just run-cli validate samples/machines/single-gpu.yaml --payload samples/payloads/ubuntu-rocm7_0.yaml --assets
   just run-cli plan samples/machines/single-gpu.yaml --payload samples/payloads/ubuntu-rocm7_0.yaml
   # 启动会话
   just run-topology samples/machines/single-gpu.yaml --payload samples/payloads/ubuntu-rocm7_0.yaml

- 串口控制台、登录与关闭流程见 :ref:`gs-first-session`\ 。
- 主机以状态 0 退出时结束本机；SIGINT 或 SIGTERM 触发有序关闭。
- ``--assets`` 会检查 QEMU、gem5、payload 内核与磁盘等文件是否存在。

验证
----

- 计划输出中只有一台机器、一个主机进程和一个设备进程，内存池 24 GiB，``mi300x-0.vram`` 位于 8 GiB。
- 客户机启动后 ``amdgpu`` 绑定模拟设备；``rocminfo`` 中的 gfx 目标为 ``gfx942``\ 。
- 仓库的 ROCm 回归由 ``scripts/ci/run_rocm.py`` 生成等价的单机单 GPU 拓扑，并在集成工作流中通过同一个 Rust 启动器运行。
- 模型与内存池另有 ``just test-gem5-mi300x`` 检查；样例本身由 render 测试加载。

限制
----

- 客户机磁盘镜像约 55 GB，首次准备需要足够的磁盘空间。
- PSP 与 SMU 未建模：不要设置 ``ip_block_mask`` 的第 3 位。
- BIOS/IP discovery 路径未建模：客户机必须在 ``modprobe`` 前把 ``mi300.rom`` 写到 ``0xC0000``\ 。
- YAML 适配器每个进程只启动一个 GPU（``--num-gpus=1``\ ），增加 GPU 需要增加设备条目，见 :doc:`gpu_8`\ 。
- 启动客户机需要 KVM；运行会话需要 Linux glibc 与 ``setpriv``\ 。

相关页面
--------

- 主机配置：:doc:`../hosts/index`
- 设备目录：:doc:`../devices/index`
- Payload：:doc:`../payloads/index`
- 机器目录：:doc:`index`
- 参考：:ref:`ref-topology-schema`\ 、:ref:`ref-device-adapters`
- 第 4 章：:ref:`sim-gem5-pci`\ 、:ref:`sim-gem5-model`\ 、:ref:`sim-guest-driver`
- 源码：``samples/machines/single-gpu.yaml``\ 、``samples/devices/gpu/mi300x.yaml``
