.. SPDX-License-Identifier: Apache-2.0

.. _launcher-index:

Cosim Launcher 介绍
====================

本页介绍 Cosim Launcher 的定位、组成和本章的阅读顺序。

Cosim Launcher 是仓库中的 Rust 程序 ``cosim``\ ，它读取 YAML 拓扑，把拓扑解析成本机执行计划，启动并监督 host QEMU 与设备进程，最后写出 verdict。拓扑解析、会话执行和命令行由 ``cosim-topology``\ 、``cosim-runtime``\ 和 ``cosim-cli``\ 三个 crate 分别承担。

启动器负责什么
---------------

- 解析：读取 YAML 文档，完成导入、模板展开、校验和内存布局（见 :doc:`yaml_pipeline`\ ）。
- 计划：结合本机页大小、``PATH``\ 和会话目录，生成进程、参数、就绪探测和资源路径。
- 执行：按依赖顺序启动进程，做就绪探测，以租约协调关闭，并处理信号升级。
- 收尾：写出 verdict 并清理会话资源；启动器异常退出后可以用 ``cosim clean``\ 回收残留资源。

本章内容
---------

.. toctree::
   :maxdepth: 1

   cli
   yaml_pipeline
   session_lifecycle
   rust_workspace
   debugging_sessions
   legacy_launcher

推荐阅读路径
-------------

- 第一次使用：先读 :doc:`cli`\ ，再按 :doc:`yaml_pipeline`\ 理解输入文档如何变成计划。
- 排查启动或关闭失败：:doc:`session_lifecycle`\ 与 :doc:`debugging_sessions`\ 。
- 修改启动器代码：:doc:`rust_workspace`\ 给出 crate 划分和适配器扩展点。
- 仍在用旧脚本：:doc:`legacy_launcher`\ 说明遗留路径及其边界。

相关章节
---------

- :ref:`arch-execution-flow`：会话执行流程的系统视图。
- :ref:`arch-components`：各组件在整体架构中的位置。
- :ref:`ref-device-adapters`：设备适配器的字段与就绪约束。
- :ref:`gs-first-session`：从零跑通第一个会话。
