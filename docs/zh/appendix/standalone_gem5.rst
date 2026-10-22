.. SPDX-License-Identifier: Apache-2.0

.. _appendix-standalone-gem5:

standalone gem5 全系统仿真
==========================

本页描述不经过 QEMU、完全在 gem5 内部运行 CPU + GPU 的全系统仿真方式，并与联合仿真
对照。它属于替代工作流，日常开发仍以联合仿真为主。

与联合仿真的区别
----------------

.. list-table::
   :header-rows: 1

   * - 方面
     - 联合仿真（QEMU + gem5）
     - standalone gem5
   * - CPU 执行
     - KVM，接近原生速度
     - gem5 atomic/timing 模型
   * - 启动时间
     - 约 30 秒
     - 约 2 到 5 分钟（KVM 快进）
   * - GPU 模型
     - gem5 MI300X，通过 vfio-user 暴露
     - 同一个 gem5 MI300X 模型
   * - 驱动加载
     - ``cosim-gpu-setup.service`` 或手动 ``modprobe``
     - 通过 ``m5 readfile`` 自动化
   * - 适用场景
     - 驱动开发、交互式调试
     - 微架构研究、性能基准测试

快速开始
--------

1. 编译 gem5 和客户机磁盘镜像，步骤与联合仿真相同。参见 :ref:`gs-install` 与
   :ref:`gs-guest-image`。
2. 编译 GPU 测试应用：

   .. code-block:: bash

      just build-gpu-app square

3. 运行仿真：

   .. code-block:: bash

      just run-gem5-fs build/apps/square/square.default

   .. warning::

      必须指定 ``--app`` 参数。不指定时 ``readfile_contents`` 为空字符串，
      驱动永远不会被加载。

4. 监控输出：

   .. code-block:: bash

      tail -f m5out/board.pc.com_1.device

仿真使用 KVM 快进 Linux 启动过程，然后自动加载 GPU 驱动并运行指定的应用。客户机在
测试完成后调用 ``m5 exit`` 结束仿真。

m5 与客户机自动化
-----------------

客户机镜像中包含 ``/sbin/m5`` 工具和驱动加载脚本
``/home/gem5/load_amdgpu.sh``。gem5 通过 ``readfile`` 把宿主机上的应用
二进制和启动参数注入客户机内存，客户机脚本读取这些内容、加载 amdgpu 驱动并执行
测试，最后用 ``m5 exit`` 通知模拟器结束。

- ``--app`` 指定的应用成为 ``readfile_contents`` 的内容。
- 应用退出后由客户机脚本调用 ``m5 exit``，否则模拟器会继续运行。
- 输出写入 ``m5out/``，串口日志文件为 ``board.pc.com_1.device``。

限制
----

- 该路径使用 gem5 的 CPU 模型，不提供 QEMU/KVM 的交互式客户机环境；启动和调试都
  比联合仿真慢。
- 样例流程以 ``square`` 应用为入口；更换应用需要重新编译并传入对应的
  ``--app`` 路径。
- 另一套 ``gpufs`` 配置、使用 ``guestfish`` 验证磁盘镜像以及构建过程
  内部原理不在本页范围，参见 gem5 官方的 GPUFS 文档：
  https://www.gem5.org/documentation/general_docs/gpu_models/gpufs

相关页面
--------

- :ref:`arch-index`
- :ref:`sim-gem5-index`
- :ref:`sim-guest-driver`
- :ref:`appendix-sst-and-placement`
