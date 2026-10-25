.. SPDX-License-Identifier: Apache-2.0

.. _contrib-patch-check:

checkpatch
==========

本页说明补丁检查的要求、本地运行方式、与上游脚本的差异以及误报的处理。

检查范围与要求
--------------

提交到本仓库的每个非合并提交都必须通过 ``scripts/host/checkpatch.pl`` 检查，且不能
出现错误。该脚本来自 QEMU 的 ``scripts/host/checkpatch.pl``，本仓库采用它所检查的
QEMU 补丁风格：

- 每个提交都带有 ``Signed-off-by:`` 行，格式必须为
  ``Signed-off-by: Name <email>``，姓名和电子邮件地址取自
  ``git config user.name`` 和 ``git config user.email``。
- 提交信息中不能出现标注 AI 的附加字段，例如标注 AI 工具的
  ``Co-authored-by:`` 行、``Assisted-by:``、
  ``Generated-by:`` 或 ``🤖`` 标记。
- 新增的行不能包含行尾空白、DOS 换行符或无效的 UTF-8 字符，文件以换行符结尾。
- 源文件使用空格缩进。超过 80 列的行产生警告，超过 90 列的行产生错误。
- 声明解释器的 Python 脚本使用 ``python3``。
- C 和 C++ 代码遵循 QEMU 编码风格：使用 ``/* */`` 注释，``if``/
  ``else`` 的所有分支都加花括号，指针写作 ``type *name``，函数的左花括号
  单独占一行。
- 新增源文件以 ``SPDX-License-Identifier:`` 行开头，不能复制许可证模板文本。
  项目许可证为 ``Apache-2.0``；来自 ``MIT``、``BSD-2-Clause`` 或
  ``BSD-3-Clause`` 许可证源码的代码可以使用这些许可证，并在提交信息中说明原因。

错误会使检查失败。警告会被报告，但不会使检查失败；提交前需要逐条确认警告。检查范围是
提交新增或修改的行；修改已有代码时，被修改的部分同样接受检查。

本地运行
--------

检查当前分支上尚未进入 ``origin/main`` 的全部提交：

.. code-block:: bash

   git fetch origin
   just check-patch

检查指定版本之后的提交：

.. code-block:: bash

   just check-patch <base-commit>

``just check-patch`` 运行 ``scripts/host/check_patch.sh``。该脚本只输出存在问题的
提交，每条报告以提交哈希和补丁行号开头；任一提交出现错误时，脚本以非零状态退出。
``just check`` 会同时运行 ``just check-patch``、ShellCheck、``just check-maintainers``
和 ``just check-cosim``，见 :doc:`workflow`。

其他输入可以直接使用 ``scripts/host/checkpatch.pl`` 检查：

.. code-block:: bash

   # 单个提交或提交范围
   ./scripts/host/checkpatch.pl HEAD
   ./scripts/host/checkpatch.pl origin/main..HEAD

   # git format-patch 生成的补丁文件
   ./scripts/host/checkpatch.pl 0001-example.patch

   # 检查整个文件（不检查 Signed-off-by）
   ./scripts/host/checkpatch.pl -f scripts/host/cosim_launch.sh

   # 检查尚未提交的补丁文件
   just check-patch-file <patch>

``scripts/host/checkpatch.pl`` 需要 Perl 5，并且必须在源码树中运行。

与 QEMU checkpatch.pl 的差异
----------------------------

``scripts/host/checkpatch.pl`` 复制自 QEMU 提交
``615ece3c406b262996e569f29ea6eed0d81c4d8d``，并包含以下修改：

.. list-table::
   :header-rows: 1

   * - 方面
     - 本仓库行为
   * - 源码树识别
     - 识别本仓库根目录（``LICENSE``、``README.md``、
       ``AGENTS.md``、``.gitmodules``、``docs``、
       ``scripts``、``tests``）
   * - SPDX 许可证
     - 首选 ``Apache-2.0``；同时接受 ``MIT``、``BSD-2-Clause``、
       ``BSD-3-Clause``
   * - SPDX 要求
     - 新增的 ``.cpp`` 和 ``.hpp`` 文件同样必须包含
       ``SPDX-License-Identifier``
   * - 许可证模板
     - 新文件中出现 Apache License 模板文本时报告错误
   * - 消息文本
     - 错误信息指向本仓库而不是 QEMU

其他检查与 QEMU 保持一致。针对 QEMU 专有路径的检查（例如
``linux-headers/``、ACPI 测试数据和 ``trace-events`` 文件）不会匹配本仓库
的路径。

该脚本保留上游的 GPL-2.0 许可证。它是开发工具，不会编译进联合仿真程序，也不会随
联合仿真程序分发。

从 QEMU 更新该脚本时，复制新的上游 ``scripts/host/checkpatch.pl``，重新应用上表中的
修改，并更新本节记录的 QEMU 提交。

误报
----

``scripts/host/checkpatch.pl`` 对正确代码报告错误时，在本仓库提交 issue，附上对应的
提交和完整报告。修复误报与更新脚本遵循同一流程。

相关页面
--------

- :doc:`workflow`
- :doc:`ci`
- :doc:`maintainers`
