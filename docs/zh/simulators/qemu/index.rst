.. SPDX-License-Identifier: Apache-2.0

.. _sim-qemu-index:

QEMU 的两个职责
================

QEMU 在本项目中以两种不同的进程出现：运行客户机的 vhost，以及导出 PCI 设备的功能模型。两者拥有独立的命令行和生命周期。

职责一：vhost
--------------

host QEMU 运行客户机 Linux、amdgpu 驱动和 ROCm 程序，负责 CPU、内存、PCIe 拓扑、直接内核启动以及 QMP 和串口管理。它把机器内存池映射为客户机内存，并把每个设备作为独立的 vfio-user 客户端挂到专用 PCIe root port 上。

职责二：device model
---------------------

设备 QEMU 使用 ``-machine x-remote`` 和 ``x-vfio-user-server``\ 导出单个 PCI 设备，例如 QEMU 自带的 ``edu``\ 教学设备。这种模式只做功能仿真，适合协议、驱动和集成测试，不提供时序模型。

本章内容
---------

.. toctree::
   :maxdepth: 1

   vhost
   device_models

推荐阅读路径
-------------

- 先读 :doc:`vhost`\ 了解客户机运行环境的构造。
- 再读 :doc:`device_models`\ 了解 vfio-user 功能设备的启动方式。
- 需要 MI300X 性能行为：转到 :doc:`../gem5/index`\ 。
- 连接协议的系统说明：:ref:`arch-vfio-user`\ 。
