.. SPDX-License-Identifier: Apache-2.0

.. _ref-topology-schema:

拓扑 YAML schema
================

本页是拓扑文档与 payload 文档字段的唯一事实源：字段名、类型、默认值、约束和上限都在这里定义，其他章节只讲用法并链接本页。机器可读的 JSON Schema 由 ``cosim schema`` 输出。

文档结构
--------

拓扑文档只描述硬件与进程布局；客户机启动输入放在独立的 payload 文档中。未知字段一律报错。

.. list-table::
   :header-rows: 1

   * - 字段
     - 类型
     - 必填
     - 默认值
     - 约束
   * - ``version``
     - integer
     - 是
     - —
     - 必须为 ``1``
   * - ``imports``
     - list<string>
     - 否
     - ``[]``
     - 相对导入文件解析，再相对 ``--samples`` （默认 ``samples/``）；支持 ``#templates`` 后缀；循环导入报错
   * - ``templates``
     - map<string, machine/host/device>
     - 否
     - ``{}``
     - 名称必须是标识符；映射递归合并，序列整体替换；模板循环报错
   * - ``kinds``
     - map<string, kind>
     - 否
     - ``{}``
     - 必填 ``role``、``model``，提供 ``argv`` 或 ``command``；``max_devices`` 只用于 host kind
   * - ``machines``
     - list<machine>
     - 是
     - ``[]``
     - 导入、模板和 ``count`` 展开后至少有一台机器，否则报错

机器
----

一台机器由一个 QEMU host、一组设备进程和一个共享内存池组成。

.. list-table::
   :header-rows: 1

   * - 字段
     - 类型
     - 必填
     - 默认值
     - 约束
   * - ``id``
     - identifier
     - 是
     - —
     - 机器标识符；``count`` 大于 1 时展开为 ``id0`` 到 ``idN``
   * - ``use``
     - template name
     - 否
     - —
     - 选择机器模板；未知引用报错
   * - ``count``
     - 正整数
     - 否
     - ``1``
     - 展开为多台机器，总数不超过 4096
   * - ``host``
     - host
     - 是
     - —
     - 见 host 字段表
   * - ``devices``
     - list<device>
     - 否
     - ``[]``
     - 数量受 host kind 的 ``max_devices`` 限制，绝对上限 256
   * - ``placement.agent``
     - 非空 string
     - 否
     - —
     - 解析后写入计划；``cosim run`` 拒绝远端放置

主机（host）
------------

host 的启动方式是 ``kinds`` 中声明的 host kind 与模板合并后的结果；``qemu-host`` 渲染 QEMU 命令行并声明 ``max_devices: 64``。

.. list-table::
   :header-rows: 1

   * - 字段
     - 类型
     - 必填
     - 默认值
     - 约束
   * - ``kind``
     - string
     - 是
     - —
     - 必须是 ``model: qemu`` 的 host kind；当前只有 ``qemu-host``
   * - ``runtime.binary``
     - path/name
     - 是
     - —
     - 相对工作区根目录，或在不含 ``/`` 时从 ``PATH`` 查找
   * - ``runtime.env``
     - map<string,string>
     - 否
     - ``{}``
     - 进程只获得该环境，加上 ``PATH`` 和 ``LANG=C``
   * - ``runtime.argv`` / ``runtime.command``
     - list / string
     - 否
     - kind 的命令模板
     - 两者互斥；覆盖 kind 的命令模板；严格 MiniJinja
   * - ``memory``
     - byte size
     - 是
     - —
     - 客户机内存，必须是执行系统页大小的整数倍
   * - ``memory_align``
     - byte size
     - 否
     - 2 MiB
     - 客户机内存在内存池中的对齐；同时是设备区域的默认对齐
   * - ``memory_map``
     - MiniJinja string
     - 含 ``gem5-mi300x`` 设备时必填
     - —
     - 渲染 1 到 64 个有序、不重叠、正好覆盖 ``memory`` 的 ``{start, size}`` 区间
   * - ``cpus``
     - 正整数
     - 是
     - —
     - QEMU ``-smp`` 值
   * - ``accel``
     - string
     - 是
     - —
     - 传给 ``-accel``，如 ``kvm``、``tcg``
   * - ``machine``
     - string
     - 是
     - —
     - QEMU machine 类型，如 ``q35``、``virt,gic-version=3``
   * - ``cpu``
     - string
     - 否
     - 无
     - 传入时添加 ``-cpu``
   * - ``display`` / ``monitor``
     - string
     - 否
     - 无
     - QEMU 后端；样例设置为 ``none``
   * - ``no_reboot``
     - bool
     - 否
     - ``false``
     - 为 true 时添加 ``-no-reboot``
   * - ``serial.wait_for``
     - string
     - 否
     - 无
     - 串口日志中的就绪标记
   * - ``serial.timeout``
     - seconds
     - 否
     - 运行级 ``--ready-timeout``
     - 需要 ``serial.wait_for``；取值 1 到 86400
   * - ``args``
     - list<string>
     - 否
     - ``[]``
     - 追加到 QEMU 命令行末尾

设备
----

设备字段描述声明形状，启动参数与就绪探测由适配器决定，见 :doc:`device_adapters`。

.. list-table::
   :header-rows: 1

   * - 字段
     - 类型
     - 必填
     - 默认值
     - 约束
   * - ``id``
     - identifier
     - 否
     - 由 ``use`` 名称或 kind 加序号组成
     - ``count`` 为 1 时保留显式 ``id``
   * - ``use``
     - template name
     - 否
     - —
     - 选择设备模板
   * - ``kind``
     - string
     - 是
     - —
     - 内置 ``gem5-mi300x``、``qemu-device``，或 ``kinds`` 中声明的 device kind
   * - ``count``
     - 正整数
     - 否
     - ``1``
     - 展开为多个设备进程
   * - ``config``
     - path
     - ``gem5-mi300x`` 必填
     - —
     - 指向 ``mi300_cosim.py``；``qemu-device`` 拒绝该字段
   * - ``ready_log``
     - 非空 string
     - 自定义命令必填
     - ``gem5-mi300x`` 的监听行
     - 设备开始监听后输出到标准输出的标记；不能含 NUL
   * - ``runtime.binary``
     - path/name
     - ``gem5-mi300x`` 可省略
     - ``gem5.opt``
     - 省略时从 ``PATH`` 查找；其他适配器必填
   * - ``runtime.env`` / ``argv`` / ``command``
     - map / list / string
     - 否
     - —
     - ``argv`` 或 ``command`` 覆盖适配器命令
   * - ``memory_regions``
     - list<{name,size,align}>
     - ``gem5-mi300x`` 恰好一个 ``vram``
     - ``align`` 2 MiB
     - 区域大小是页的整数倍；对齐是大于等于一页的 2 的幂
   * - ``pci``
     - {vendor_id, device_id, msix_vectors, rom}
     - 否
     - —
     - MI300X 值固定为 ``0x1002`` 与 ``0x74a0``、256 个 MSI-X；提供时必须匹配；``msix_vectors`` 取值 1 到 2048
   * - ``args``
     - map<string, any>
     - 否
     - ``{}``
     - 适配器特定参数，见设备适配器页
   * - ``guest_hints``
     - {modprobe, cmdline}
     - 否
     - —
     - ``cmdline`` 需要带 ``boot.kernel`` 的 payload；``modprobe`` 只写入计划

payload 文档
------------

payload 独立于拓扑选择，应用于拓扑中的每一台机器。仅描述硬件的拓扑可以省略 payload；设备声明 ``guest_hints.cmdline`` 时必须提供带 ``boot.kernel`` 的 payload。

.. list-table::
   :header-rows: 1

   * - 字段
     - 类型
     - 必填
     - 默认值
     - 说明
   * - ``boot.kernel``
     - path
     - 否
     - 无
     - 启用直接内核启动；host 添加 ``-kernel``
   * - ``boot.initrd``
     - path
     - 否
     - 无
     - 需要 ``boot.kernel``
   * - ``boot.cmdline``
     - string
     - 否
     - 无
     - 与每台机器所有设备的 ``guest_hints.cmdline`` 空格连接

.. list-table::
   :header-rows: 1

   * - 字段
     - 类型
     - 必填
     - 默认值
     - 说明
   * - ``id``
     - identifier
     - 是
     - —
     - payload 内唯一，忽略 ASCII 大小写
   * - ``path`` / ``backing``
     - path
     - 二选一
     - —
     - ``path`` 是源镜像；``backing`` 是 overlay 的基底
   * - ``format``
     - ``raw`` / ``qcow2``
     - 否
     - ``qcow2``
     - 源镜像格式
   * - ``bus``
     - ``virtio`` / ``nvme`` / ``ide`` / ``scsi``
     - 否
     - ``virtio``
     - 客户机挂载总线
   * - ``boot``
     - bool
     - 否
     - ``false``
     - 整个 payload 中至多一个 ``true``
   * - ``create`` + ``size``
     - bool + byte size
     - 否
     - ``false`` / 无
     - ``create: true`` 需要 ``path`` 和 ``size``；``size`` 只在创建时使用
   * - ``readonly`` / ``shared``
     - bool
     - 否
     - overlay
     - ``shared: true`` 要求 ``readonly: true``；直接写入要求 ``readonly: false`` 且 ``shared: false``
   * - ``snapshot`` （payload 级）
     - bool
     - 否
     - ``false``
     - 为每台机器创建 qcow2 overlay

``snapshot`` 是 payload 级布尔字段：为 true 时所有磁盘都按 overlay 处理，即使声明了 ``readonly: false`` 和 ``shared: false``。

资源路径与标识符
----------------

- 资源路径相对工作区根目录解析（``COSIM_WORKSPACE``，未设置时为当前目录），包括带 ``/`` 的可执行文件、``config``、``pci.rom``、``boot.kernel``、``boot.initrd``、磁盘的 ``path`` 和 ``backing``。

- 相对路径不能包含 ``..``；绝对路径允许。不含 ``/`` 的可执行文件名从 ``PATH`` 查找。

- 标识符由 1 到 48 个 ASCII 字母、数字、下划线或连字符组成；机器、设备和磁盘标识符忽略 ASCII 大小写后必须唯一。

- 机器标识符 ``memory``，以及设备标识符 ``host``、``qmp``、``serial`` 由会话布局保留。

默认值与上限
------------

.. list-table::
   :header-rows: 1

   * - 项目
     - 默认值或上限
     - 来源
   * - 区域对齐默认值
     - 2 MiB
     - ``crates/cosim-topology/src/resolve.rs``
   * - 磁盘格式 / 总线默认值
     - ``qcow2`` / ``virtio``
     - ``crates/cosim-topology/src/model.rs``
   * - 机器总数上限
     - 4096
     - ``crates/cosim-topology/src/resolve.rs``
   * - 每台机器设备数上限
     - host kind 的 ``max_devices`` （``qemu-host`` 为 64），绝对上限 256
     - ``crates/cosim-topology/src/resolve.rs``
   * - 标识符
     - 1 到 48 个 ASCII 字母、数字、``_`` 或 ``-``；忽略大小写唯一
     - ``crates/cosim-topology/src/model.rs``
   * - 保留名
     - 机器 ``memory``；设备 ``host``、``qmp``、``serial``
     - ``crates/cosim-runtime/src/layout.rs``
   * - 串口标记超时
     - 1 到 86400 秒
     - ``crates/cosim-topology/src/resolve.rs``
   * - 就绪超时默认值
     - 120 秒（``--ready-timeout``）
     - ``crates/cosim-cli/src/main.rs``
   * - 运行目录默认值
     - ``.cosim/<12-hex>``
     - ``crates/cosim-cli/src/main.rs``
   * - 内存池目录默认值
     - Linux 为 ``/dev/shm/cosim-<name>-<hash>``，其他系统为 ``<run-dir>/memory``
     - ``crates/cosim-runtime/src/layout.rs``
   * - 磁盘锁目录
     - ``~/.cache/cosim-gpu/disk-locks`` （``COSIM_DISK_LOCK_DIR``）
     - ``crates/cosim-runtime/src/env.rs``

来源与维护
----------

字段定义来自以下文件，修改时需同步本页表格：

- ``crates/cosim-topology/src/raw.rs``：YAML 解码类型。

- ``crates/cosim-topology/src/model.rs``：校验后的类型与枚举取值。

- ``crates/cosim-topology/src/resolve.rs``：默认值、约束与上限。

- ``crates/cosim-runtime/src/layout.rs``：会话路径与保留名。

- ``samples/``：仓库测试会加载并渲染全部样例，可作为合法配置的活样例。

更新后运行以下命令核对：

.. code-block:: bash

   just run-cli schema
   just run-cli schema --payload
   just run-cli validate samples/machines/single-gpu.yaml --payload samples/payloads/ubuntu-rocm7_0.yaml --assets
   just check-cosim

相关页面
--------

- 设备启动约定：:doc:`device_adapters`

- 客户机驱动参数：:doc:`guest_parameters`

- 拓扑写法与示例：:ref:`topo-write-topology`

- payload 与客户机镜像：:ref:`topo-payloads`

- YAML 加载与计划生成流程：:ref:`launcher-yaml-pipeline`
