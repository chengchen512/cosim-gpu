.. SPDX-License-Identifier: Apache-2.0


.. _topo-write-topology:

如何编写拓扑 YAML
=================

本页给出编写拓扑文档的步骤：从文档骨架开始，用导入和模板复用主机与设备定义，展开机器与设备数量，最后用 ``validate``\ 、``plan``\ 、``graph`` 检查结果。字段全集与默认值见 :ref:`ref-topology-schema`\ 。

文档骨架
--------

拓扑文档固定为 ``version: 1``\ ，可包含 ``imports``\ 、``templates``\ 、``kinds`` 和 ``machines``\ ；未知字段会报错。

.. code-block:: yaml

   version: 1
   imports:
     - hosts/qemu.yaml
     - devices/gpu/mi300x.yaml
     - devices/pci/qemu-edu.yaml
   machines:
     - id: m0
       host: {use: host-x86, memory: 32G}
       devices:
         - {use: mi300x, count: 2}
         - {use: qemu-edu, count: 2}

- 客户机启动输入（内核、命令行、磁盘）不在拓扑里，而是放在 payload 文档中，运行或校验时用 ``--payload`` 选择；一个 payload 应用于所有机器。
- ``cosim schema`` 输出拓扑格式的 JSON Schema，``cosim schema --payload`` 输出 payload 的 schema。
- 资源路径相对于工作区根目录解析，包括含 ``/`` 的可执行文件、设备的 ``config`` 与 ``pci.rom``\ 、payload 的 ``boot.kernel`` 与 ``boot.initrd``\ 、以及磁盘的 ``path`` 与 ``backing``\ 。不含 ``/`` 的可执行文件名在生成计划时从 ``PATH`` 查找。

导入与模板
----------

- 导入路径先相对于导入它的文件解析，再相对于 ``--samples`` 目录（默认 ``samples/``\ ）解析；可以使用 ``#templates`` 后缀。
- 被导入文件贡献模板、kind 和进一步的导入；只有顶层文档贡献可运行的机器。
- ``use`` 选择模板；映射递归合并，序列整体替换，显式写出的值覆盖模板值。
- 导入循环、模板循环、重复的模板或 kind 名称以及未知引用都会报错；同一个文件经多条路径导入只加载一次。
- 仓库中的分层约定：``samples/hosts/`` 与 ``samples/devices/`` 不导入其他文件，``samples/machines/`` 导入二者，``samples/clusters/`` 导入机器文件。

.. code-block:: text

   hosts/ ───┐
   devices/ ─┴──> machines/ ───> clusters/

机器、设备与 count
------------------

- ``count`` 把 ``id: m, count: 4`` 展开为 ``m0`` 到 ``m3``\ ；机器总数最多 4096 台。
- 设备标识符默认由 ``use`` 名称或 kind 加序号组成，例如 ``mi300x-0``\ ；显式写出的 ``id`` 在 count 为 1 时保留。
- 标识符由 1 到 48 个字母、数字、下划线或连字符组成；机器、设备和磁盘标识符不能只在 ASCII 大小写上不同。
- 机器标识符 ``memory`` 与设备标识符 ``host``\ 、``qmp``\ 、``serial`` 由会话布局保留。
- 一台机器的设备数量不能超过主机 kind 的 ``max_devices``\ ，``qemu-host`` 为 64。
- ``placement.agent`` 只被解析和保存，``cosim run`` 拒绝远端放置。

主机与设备字段
--------------

主机声明 ``kind``\ 、``runtime.binary``\ 、``runtime.env``\ 、``memory``\ 、``cpus``\ 、``accel`` 和 QEMU ``machine``\ ；可选字段包括 ``cpu``\ 、``display``\ 、``monitor``\ 、``no_reboot``\ 、``memory_align``\ 、``memory_map``\ 、``serial`` 与 ``args``\ 。设备由 ``kind`` 选择启动约定：

.. list-table::
   :header-rows: 1

   * - kind
     - 用途
     - 需要的字段
   * - ``gem5-mi300x``
     - gem5 MI300X 性能模型
     - ``config``\ 、恰好一个 2 的幂大小的 ``vram`` 区域、主机的 ``memory_map``
   * - ``qemu-device``
     - 通过 vfio-user 导出的 QEMU 设备
     - ``runtime.binary`` 与 ``args.device.driver``\ ；不接受 ``config`` 和私有内存区域
   * - 声明的 device kind
     - 自定义启动命令（扩展点）
     - ``kinds`` 中的 ``role: device`` 与 ``argv`` 或 ``command``\ ；``ready_log``

完整字段表与适配器契约分别在 :ref:`ref-topology-schema` 与 :ref:`ref-device-adapters`\ ；主机 profile 见 :doc:`hosts/index`\ ，设备种类见 :doc:`devices/index`\ 。

Payload 与磁盘
--------------

payload 文档包含 ``boot``\ （``kernel``\ 、``initrd``\ 、``cmdline``\ ）、``disks`` 与 ``snapshot``\ 。磁盘的写模式由声明决定：

.. list-table::
   :header-rows: 1

   * - 声明
     - 行为
   * - ``readonly: true``
     - 以只读方式打开源镜像
   * - ``readonly: false`` 加 ``shared: false``
     - 直接写 ``path``\ ；若声明 ``backing`` 或 payload 设置 ``snapshot: true``\ ，改为每台机器一个 qcow2 overlay
   * - 不写 ``readonly``
     - 在会话目录为每台机器写一个 qcow2 overlay；``shared: true`` 要求 ``readonly: true``
   * - ``create: true`` 加 ``size``
     - 用 ``qemu-img`` 创建缺失的 ``path``\ ；先以临时名称格式化，再通过链接发布
   * - 多个磁盘引用同一路径
     - 直接写入的磁盘不能与其他磁盘共用镜像；创建请求必须使用相同的大小与格式

payload 结构与配对限制见 :doc:`payloads/index`\ ；磁盘字段的权威说明在 :ref:`ref-topology-schema`\ 。

校验、预览与运行
----------------

.. code-block:: bash

   # 检查结构、标识符与内存布局；--assets 还会检查本地文件是否存在
   just run-cli validate samples/machines/gpu-8.yaml --payload samples/payloads/ubuntu-rocm7_0.yaml --assets
   # 打印可执行文件、参数、环境、就绪探测、内存布局与磁盘目标
   just run-cli plan samples/machines/mixed-models.yaml --payload samples/payloads/ubuntu-rocm7_0.yaml
   # 打印机器与 vfio-user 边的 Mermaid 图
   just run-cli graph samples/clusters/cluster-4x8.yaml
   # 查看格式的 JSON Schema
   just run-cli schema
   # 启动会话
   just run-topology samples/machines/single-gpu.yaml --payload samples/payloads/ubuntu-rocm7_0.yaml

- ``validate`` 不启动进程；``plan`` 输出 ``run`` 将要执行的计划；``graph`` 只读取文档。
- ``--assets`` 与真正的会话启动会检查 ``runtime.binary``\ 、``config``\ 、``pci.rom`` 等文件是否存在。
- 运行会话需要 Linux glibc 与 ``setpriv``\ ；其他系统通过开发容器执行，见 :ref:`gs-platform-container`\ 。

源码与证据
----------

- 解析与校验：``crates/cosim-topology/src/raw.rs``\ 、``crates/cosim-topology/src/resolve.rs``\ 、``crates/cosim-topology/src/model.rs``\ 。
- 计划与布局：``crates/cosim-topology/src/layout.rs``\ 、``crates/cosim-runtime/src/plan.rs``\ 。
- 命令入口与选项：``crates/cosim-cli/src/main.rs``\ 。
- 可运行样例：``samples/machines/``\ 、``samples/clusters/``\ 。

相关页面
--------

- 单机与多机：:doc:`single_machine`\ ，:doc:`multi_machine`
- 机器目录：:doc:`machines/index`
- 主机与设备：:doc:`hosts/index`\ ，:doc:`devices/index`
- Payload：:doc:`payloads/index`
- Schema 参考：:ref:`ref-topology-schema`
