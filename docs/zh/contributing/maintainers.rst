.. SPDX-License-Identifier: Apache-2.0

.. _contrib-maintainers:

维护者与 area
=============

``MAINTAINERS.yml`` 把仓库划分为多个 area，记录每个 area 的维护者、协作者与
标签。本页说明如何查询归属、相关检查、自动分配以及新增维护者。

area 与文件归属
---------------

每个 area 可以包含 ``status``、``maintainers``、``collaborators``、
``inform``、``labels``、``files``、``files-regex``、
``file-groups`` 和 ``description`` 字段。格式说明位于文件开头的注释中。

- ``status`` 取 ``maintained``、``odd fixes``、
  ``unmaintained`` 或 ``obsolete``。
- 每个受版本控制的文件都必须属于至少一个 area；
  ``just check-maintainers`` 会在 CI 中强制检查。
- 提交在现有 area 之外新增文件时，在同一个提交中更新 ``MAINTAINERS.yml``。

查询维护者
----------

``scripts/host/get_maintainer.py`` 读取 ``MAINTAINERS.yml``。先安装一次
Python 依赖：

.. code-block:: bash

   pip install -r scripts/ci/requirements.txt

然后通过 just 查询：

.. code-block:: bash

   just maint-paths scripts/host/cosim_launch.sh tests/   # 查询路径所属 area
   just maint-commits origin/main..                  # 查询提交涉及的 area
   just maint-areas                                  # 列出全部 area 和维护者

``python3 scripts/host/get_maintainer.py --help`` 列出其他子命令，例如
``orphaned`` 和 ``count``。

检查
----

.. list-table::
   :header-rows: 1

   * - 检查
     - 位置
     - 失败条件
   * - ``just check-maintainers``
     - ``ci.yml`` 中的 ``Maintainers`` 任务
     - ``MAINTAINERS.yml`` 出现未知字段、错误的状态值、格式错误的列表、
       不匹配任何文件的通配模式、缺少结尾 ``/`` 的目录通配模式、无效的正则
       表达式，或者处于 maintained 状态却没有维护者的 area；或者某个受版本控制的
       文件不属于任何 area
   * - ``scripts/ci/check_maintainer_changes.py``
     - ``assigner.yml``
     - 拉取请求新增的维护者或协作者在仓库中没有 triage 及以上权限

自动分配
--------

指向 ``main`` 的拉取请求被创建、更新、重新打开或标记为可审查时，
``.github/workflows/assigner.yml`` 运行
``scripts/ci/set_assignees.py``：

- 为拉取请求添加所有受影响 area 的标签。
- 请求所有受影响 area 的维护者和协作者审查，拉取请求作者和主动退出审查的人除外。
- 把修改文件最多的 area 的维护者设为负责人。作者是该 area 唯一的维护者时，改用
  下一个 area。只有在没有其他 area 受影响时，才把 ``Documentation`` 的维护者
  设为负责人。
- ``MAINTAINERS.yml`` 发生变化时，同时请求所有变化 area 的维护者审查。

问题被添加标签时，把拥有这些标签的 area 的维护者设为负责人。

该工作流使用 ``pull_request_target``，运行 ``main`` 分支上的脚本。它只把
拉取请求中的 ``MAINTAINERS.yml`` 当作数据读取，因此来自派生仓库的拉取请求
无法改变工作流执行的内容。

添加维护者
----------

1. 在 GitHub 仓库中为该用户授予 triage 及以上权限。
2. 在 ``MAINTAINERS.yml`` 对应 area 的 ``maintainers`` 或
   ``collaborators`` 下添加该用户的 GitHub ID。
3. 提交拉取请求。系统会请求该 area 现有维护者审查；如果跳过了第 1 步，权限检查会
   失败。

相关页面
--------

- :doc:`workflow`
- :doc:`patch_check`
- :doc:`ci`
