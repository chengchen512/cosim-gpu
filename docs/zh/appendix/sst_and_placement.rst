.. SPDX-License-Identifier: Apache-2.0

.. _appendix-sst-and-placement:

SST 实验与远程 placement
========================

本页记录仓库中 SST 相关配置的数据模型与当前状态，以及拓扑中远程 placement 字段的
实际行为。

SST 数据模型
------------

``configs/sst/`` 保存独立的 SST（Structural Simulation Toolkit）实验配置：

- ``multi_node_topology.py`` 描述 SST 多节点网络的参数；
- ``mi300x_merlin_poc.py`` 提供 MI300X 与 SST/Merlin 的集成实验。

这些配置依赖相应的模拟器组件，并具有独立于 Rust 进程管理的接口。它们不属于
``cosim run`` 的启动路径，也不由 launcher 生成执行计划。

在多 GPU 互联方面，gem5 的 ``XGMIBridge`` 及相关配置实现模拟器内部的互联
行为；gem5 的 Python 配置也支持通过 ``--num-gpus`` 在单个 gem5 进程内创建多个
GPU 对象及其互联。YAML 的 MI300X 适配器采用另一种方式：为每个进程启动一个 GPU，
并为每个 GPU 分配一个 VRAM 区域。

远程 placement 规则
-------------------

拓扑的 ``placement.agent`` 字段用于指定分布式执行使用的远端 agent。当前执行器
的行为如下：

- 远程 placement 可以在配置中描述，但 ``cosim run`` 在分配资源之前拒绝执行。
- 交换机（switch）节点是设计中的预留部分，尚未进入拓扑格式。
- 本地执行路径只运行本机进程，不建立跨机器的模拟器互联。

因此，SST 实验与远程 placement 目前都只是可描述、不可由 ``cosim run`` 执行的
配置形态。

当前状态与限制
--------------

- SST 配置是独立的实验路径，当前不可由 ``cosim run`` 执行，需要对应的外部
  模拟器组件。
- 仓库的多机拓扑通过 ``count`` 在单机内展开机器数量，属于本地执行路径；跨机器
  的模拟器互联只在 SST 配置中表达。
- 拓扑格式对 ``placement`` 与交换机节点保持保守：前者在运行前被拒绝，后者尚未
  加入格式。

相关页面
--------

- :ref:`sim-gem5-multi-gpu`
- :ref:`topo-write-topology`
- :ref:`ref-topology-schema`
- :ref:`topo-multi-machine`
