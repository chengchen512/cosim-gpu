.. SPDX-License-Identifier: Apache-2.0


.. _topo-payloads:

Payload 与客户机镜像
====================

payload 是独立的 YAML 文档，提供客户机启动输入：内核、命令行与磁盘。它在校验或运行时通过 ``--payload`` 选择，并应用到拓扑中的每一台机器；只描述硬件的拓扑可以省略 payload。本页说明 payload 结构、随仓库提供的 Ubuntu + ROCm payload、客户机镜像事实与配对约束。

Payload 文档结构
----------------

.. list-table::
   :header-rows: 1

   * - 字段
     - 必需
     - 默认
     - 说明
   * - ``version``
     - 是
     - 无
     - 必须为 ``1``
   * - ``boot.kernel``
     - 否
     - 无
     - 启用直接内核启动
   * - ``boot.initrd``
     - 否
     - 无
     - 依赖 ``kernel``
   * - ``boot.cmdline``
     - 否
     - 无
     - 与设备的 ``guest_hints.cmdline`` 空格连接
   * - ``disks[].id``
     - 是
     - 无
     - payload 内唯一；标识符大小写不敏感
   * - ``disks[].path``\ 、``backing``
     - 二选一
     - 无
     - 源镜像路径，或 overlay 的基底镜像
   * - ``disks[].format``
     - 否
     - ``qcow2``
     - ``raw`` 或 ``qcow2``
   * - ``disks[].bus``
     - 否
     - ``virtio``
     - ``virtio``\ 、``nvme``\ 、``ide`` 或 ``scsi``
   * - ``disks[].boot``
     - 否
     - ``false``
     - 最多一个启动盘
   * - ``disks[].create`` 加 ``size``
     - 否
     - ``false``\ 、无
     - 用 ``qemu-img`` 创建缺失的镜像
   * - ``disks[].readonly``\ 、``shared``
     - 否
     - overlay 模式
     - 组合规则见磁盘模式
   * - ``snapshot``
     - 否
     - ``false``
     - 强制每台机器写一个 qcow2 overlay

随仓库提供的 payload
--------------------

.. code-block:: yaml

   # samples/payloads/ubuntu-rocm7_0.yaml
   version: 1
   boot:
     kernel: build/rocm-local-installed/kernel
     cmdline: >-
       console=ttyS0 root=/dev/vda1 rw nokaslr modprobe.blacklist=amdgpu
   disks:
     - id: root
       backing: build/rocm-local-installed/disk
       format: raw
       bus: virtio
       boot: true

- 内核与磁盘来自镜像构建产物目录 ``build/rocm-local-installed/``\ 。
- ``cmdline`` 使用 ``ttyS0`` 作为控制台，并用 ``modprobe.blacklist=amdgpu`` 推迟驱动加载，由客户机初始化服务统一加载。
- 磁盘声明 ``backing`` 与 ``raw`` 格式：源镜像作为 overlay 基底，每台机器在会话目录写自己的 qcow2 overlay。
- 首次运行前需要准备镜像，见 :ref:`gs-guest-image`\ 。

客户机镜像
----------

.. list-table::
   :header-rows: 1

   * - 组件
     - 值
     - 说明
   * - 发行版
     - Ubuntu 24.04.2 LTS
     - 唯一的镜像 recipe 位于 ``resources/images/recipes/ubuntu/24.04/x86_64/rocm7_0/``
   * - 内核
     - 6.8.0-124-generic
     - ``amdgpu-dkms`` 模块与该内核匹配
   * - ROCm
     - 7.0
     - 安装 ``amdgpu`` 与 ``rocm`` 包
   * - 系统盘
     - 约 55 GB
     - ``just build-m5`` 与 ``just build-disk`` 产出 kernel 与 disk
   * - 架构
     - x86_64
     - 没有 AArch64 客户机镜像
   * - initrd
     - 不提供
     - 直接内核启动使用配对的内核
   * - 客户机初始化
     - ``cosim-gpu-setup.service``
     - 写 ROM 并以固定参数加载 ``amdgpu``

- 镜像内容与构建方式的完整说明见 :ref:`gs-guest-image`\ ；驱动参数以 :ref:`ref-guest-parameters` 为准，驱动要求见 :ref:`sim-guest-driver`\ 。
- 内核与磁盘必须来自同一次镜像构建：DKMS 模块只匹配配对的内核。

磁盘模式
--------

.. list-table::
   :header-rows: 1

   * - 模式
     - 声明
     - 行为
   * - 只读源
     - ``readonly: true``
     - 以只读方式打开源镜像；可以加上 ``shared: true`` 供多个磁盘共用
   * - 直接写
     - ``readonly: false`` 与 ``shared: false``
     - 直接写 ``path``\ ；同一镜像不能被拓扑中其他磁盘共用
   * - 每机器 overlay
     - 不写 ``readonly``\ ，或声明 ``backing``\ ，或设置 ``snapshot: true``
     - 在会话目录为每台机器写一个 qcow2 overlay，源镜像保持不变
   * - 创建
     - ``create: true`` 加 ``size``
     - 用 ``qemu-img`` 创建缺失的 ``path``\ ；先以临时名称格式化，再通过链接发布

- ``shared: true`` 要求 ``readonly: true``\ ；``readonly: false`` 要求 ``shared: false``\ 。
- 磁盘字段的权威说明在 :ref:`ref-topology-schema`\ ，磁盘锁与直接写入者的排他规则见 :ref:`launcher-session-lifecycle`\ 。

配对与约束
----------

- 一个 payload 应用于拓扑中的全部机器；格式中没有 per-machine payload 或磁盘映射，多机因此启动内容相同的磁盘（每台机器各有一份 overlay）。
- host profile 只描述硬件与 QEMU 设置；只有 ``boot.kernel`` 才启用直接内核启动。
- 含 ``guest_hints.cmdline`` 的设备要求 payload 包含 ``boot.kernel``\ ，否则校验失败。
- ``boot.cmdline`` 与设备 ``guest_hints.cmdline`` 用空格连接后传给 QEMU 的 ``-append``\ 。
- 没有 initrd：直接内核启动依赖与镜像配对的内核。
- 客户机镜像只有 x86_64；AArch64 样例不启动客户机，见 :doc:`../machines/aarch64`\ 。
- 运行时内存池、overlay 与 socket 位于会话目录；源镜像只读打开或通过镜像租约独占。

相关页面
--------

- 机器目录：:doc:`../machines/index`
- 单机与多机：:doc:`../single_machine`\ 、:doc:`../multi_machine`
- 编写拓扑：:doc:`../write_topology`
- 镜像准备：:ref:`gs-guest-image`
- 客户机参数：:ref:`ref-guest-parameters`
- 驱动要求：:ref:`sim-guest-driver`
- 源码：``samples/payloads/ubuntu-rocm7_0.yaml``\ 、``crates/cosim-topology/src/raw.rs``
