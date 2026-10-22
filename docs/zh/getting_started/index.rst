.. SPDX-License-Identifier: Apache-2.0

.. _gs-index:

快速开始
========

本章从干净检出开始，依次完成环境检查、组件构建、客户机资产准备、第一次联合
仿真会话和客户机内验证。

本章内容
--------

.. toctree::
   :maxdepth: 1

   requirements
   install
   guest_image
   first_session
   verify_guest
   platforms/linux
   platforms/container
   next_steps

推荐阅读路径
------------

- 第一次使用：按 :doc:`requirements` → :doc:`install` →
  :doc:`guest_image` → :doc:`first_session` → :doc:`verify_guest` 的顺序执行。
- 已经构建过客户机资产：直接从 :doc:`first_session` 开始。
- 在 macOS 或 Windows 上：先读 :doc:`platforms/container`，再按同一顺序执行；
  可引导的 KVM 客户机仍需要 Linux 主机与 KVM。
- 想了解平台差异与依赖：直接读 :doc:`platforms/linux` 或
  :doc:`platforms/container`。

预期
----

.. list-table::
   :header-rows: 1

   * - 项目
     - 预期
   * - 磁盘
     - 约 120 GB 可用空间：客户机镜像约 55 GB，另需构建产物
   * - 内存
     - 16 GB 以上；链接阶段内存不足时使用 ``just build-gem5 1``
   * - 首次构建
     - 视 CPU 核数与缓存情况，从数十分钟到数小时
   * - 首次会话
     - 客户机启动到 GPU 就绪约数分钟，其中初始化服务约 40 秒
   * - 产物位置
     - 构建产物在 ``build/``，会话目录在 ``.cosim/``

.. tip::

   构建、启动和检查任务都是顶层 ``justfile`` 中的 recipe；运行
   ``just --list`` 查看完整列表。

相关页面
--------

- :doc:`requirements`
- :doc:`first_session`
- :ref:`整体架构介绍 <arch-index>`
- :ref:`Cosim Launcher 介绍 <launcher-index>`
