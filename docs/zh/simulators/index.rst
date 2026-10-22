.. SPDX-License-Identifier: Apache-2.0

.. _sim-index:

QEMU 与 gem5 介绍
==================

本章介绍协同仿真中的两个模拟器：QEMU 负责客户机运行环境与功能仿真，gem5 负责 MI300X 的性能仿真。

功能仿真与性能仿真
-------------------

QEMU 作为 vhost 运行客户机 Linux、amdgpu 驱动和 ROCm 程序，提供 CPU、内存与 PCIe 等运行环境。它也可以作为 device model 进程，通过 vfio-user 导出 PCI 设备，只保证功能正确，不提供微架构时序。gem5 则对 MI300X 的命令处理器、执行单元、缓存和内存层次建模，提供性能相关的时序行为。

.. list-table::
   :header-rows: 1

   * - 仿真器
     - 角色
     - 关注点
   * - QEMU（vhost）
     - 客户机运行环境
     - CPU、内存、PCIe、启动、QMP 与串口
   * - QEMU（device model）
     - PCI 设备功能模型
     - 配置空间、BAR、中断等功能行为
   * - gem5
     - MI300X 性能模型
     - PM4/SDMA、IH、GPU VM、Shader/CU 与 Ruby 内存层次

设备实现的选择
---------------

拓扑通过设备适配器决定设备由谁实现：``gem5-mi300x``\ 使用 gem5 的 MI300X 性能模型，``qemu-device``\ 使用 QEMU 提供的功能设备模型，``mixed-models``\ 机器同时使用两类设备。第 5 章在机器目录中标注每个机器用到的适配器，适配器契约见 :ref:`ref-device-adapters`\ 。

本章内容
---------

.. toctree::
   :maxdepth: 1

   qemu/index
   gem5/index
   guest_driver
   debugging_models

推荐阅读路径
-------------

- 先理解两个仿真器的分工：本页与 :doc:`qemu/index`\ 、:doc:`gem5/index`\ 。
- 关心客户机如何启动：:doc:`qemu/vhost`\ 。
- 关心 QEMU 功能设备模型：:doc:`qemu/device_models`\ 。
- 关心 MI300X 模型细节：:doc:`gem5/mi300x_pci`\ 及其后的页面。
- 驱动与模型调试：:doc:`guest_driver`\ 、:doc:`debugging_models`\ 。
