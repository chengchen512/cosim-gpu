.. SPDX-License-Identifier: Apache-2.0


.. _topo-index:

拓扑结构与硬件支持
==================

本章回答三个问题：一个拓扑 YAML 文档能描述哪些组合、仓库里有哪些可以直接运行的机器（板卡）、以及每台机器由哪些主机配置、设备和 payload 组成。拓扑本身只描述硬件与进程组合，客户机启动输入来自单独的 payload 文档。

三层模型
--------

.. list-table::
   :header-rows: 1

   * - 层
     - 回答的问题
     - 页面
   * - 拓扑族
     - 一个 YAML 文档描述一台还是多台机器？
     - :doc:`single_machine`\ 、:doc:`multi_machine`
   * - 机器（板卡）
     - 哪种"主机 + 设备 + 内存池"组合可以直接运行？
     - :doc:`machines/index`
   * - 组件
     - 主机配置、设备模型与 payload 分别接受什么？
     - :doc:`hosts/index`\ 、:doc:`devices/index`\ 、:doc:`payloads/index`

.. mermaid::

   flowchart TD
       T[拓扑族] --> M[机器 / 板卡]
       M --> H[主机配置]
       M --> D[设备]
       M --> P[Payload]

本章内容
--------

.. toctree::
   :maxdepth: 1

   single_machine
   multi_machine
   write_topology
   machines/index
   hosts/index
   devices/index
   payloads/index

推荐阅读路径
------------

- 第一次接触：:doc:`single_machine` → :doc:`machines/index` → :doc:`machines/single_gpu` → :doc:`payloads/index`\ 。
- 要写自己的拓扑：先读 :doc:`write_topology`\ ，再对照 :doc:`machines/index` 中的样例改动。
- 关心多 GPU 或混合设备：:doc:`machines/gpu_8`\ ，:doc:`machines/mixed_models`\ 。
- 要把多台机器放进一个会话：:doc:`multi_machine`\ 。
- 需要主机与设备的完整字段：:doc:`hosts/index`\ 、:doc:`devices/index`\ ，以及 :ref:`ref-topology-schema`\ 、:ref:`ref-device-adapters`\ 。

相关页面
--------

- 首次会话与命令：:ref:`gs-first-session`\ 、:ref:`launcher-cli`
- 内存池与 vfio-user：:ref:`arch-memory-model`\ 、:ref:`arch-vfio-user`
- 设备模型细节：:ref:`sim-qemu-index`\ 、:ref:`sim-gem5-index`
