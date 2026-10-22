.. SPDX-License-Identifier: Apache-2.0

.. _contrib-documentation:

文档规范与双语规则
==================

本页规定文档的源格式、中英文同步规则、页面模板与格式规范，以及构建和检查命令。
修改 ``docs/`` 下任何页面之前先阅读本页。

源格式与技术栈
--------------

- 文档源文件是 ``docs/`` 下的 reStructuredText（``.rst``），不使用 MyST 或
  Markdown。
- 构建使用 Sphinx 与 ``sphinx_rtd_theme`` 主题，另有 ``sphinx-design``、
  ``sphinx-copybutton`` 和 ``sphinxcontrib-mermaid`` 扩展；配置见
  ``docs/conf.py``。
- 构建出的站点（GitHub Pages）是唯一的发布形态；``docs/README.md`` 与
  ``docs/NOTICE.md`` 不属于站点页面。
- 中文是主语言（``docs/zh/``），英文是同步镜像（``docs/en/``）。

中文优先与英文镜像
------------------

- 每个页面在 ``docs/zh/`` 与 ``docs/en/`` 中各有一个文件，相对路径相同，
  文件名使用 snake_case，扩展名为 ``.rst``。
- 先写中文，英文页面在同一改动中同步更新；不允许只改一种语言。
- 页面第一行不再写语言链接。站点的语言切换器负责切换，渲染后的页面不出现指向
  另一语言版本的首行链接。
- 两种语言的标题层级骨架必须一致：相同数量的 H2、H3，顺序也相同。
  ``docs/scripts/check_i18n.py`` 会比较每个页面的标题层级序列。
- 修改文档后运行 ``just docs-check``，它会构建两种语言并执行双语与站点检查。

章节索引页模板
--------------

章节索引页只做导航：一句话说明本章回答什么问题，然后给出 toctree 与推荐路径。
索引页不超过 80 行，细节必须落在子页面。

.. code-block:: rst

   .. _chapter-index:

   章节标题
   ========

   一句话说明本章回答什么问题、适合哪些读者。

   本章内容
   --------

   .. toctree::
      :maxdepth: 1

      page_one
      page_two

   推荐路径
   --------

   - 第一次接触：先看 page_one
   - 需要查表：直接看 page_two

标题与页面结构
--------------

- 每页只有一个 H1，内容与左侧导航标题一致。
- 正文只使用 H2 分节，必要时使用 H3；不使用 H4 或更深的标题。
- 每个页面顶部显式声明标签，例如 ``.. _contrib-workflow:``，供跨页引用。
- 每页末尾统一设置"相关页面"一节，放 3 到 6 个 ``:doc:`` 或 ``:ref:``
  链接。
- 页面标题的层级骨架在中文与英文之间保持一致。

RST 书写约定
------------

- 命令使用 ``.. code-block:: bash`` 代码块（或对应语言）；代码块内不写 shell 提示符，
  保持命令可以直接复制。
- 数据表格优先使用 ``.. list-table::`` 并带 ``:header-rows: 1``，列数不超过
  6；需要多段落单元格时才使用 ``grid-table``。
- 提示框只使用 ``note``、``tip`` 和 ``warning``，不新增自定义样式。
- 行内字面量使用双反引号包裹，例如 ``just docs-check``。
- 同章页面之间使用 ``:doc:`` 链接；跨章引用只使用 ``:ref:`` 加已有标签。
- 架构图使用 ``.. mermaid::`` 指令。
- 文件名保持 snake_case，章节索引固定为 ``index.rst``，文件名不翻译。
- 长段落使用语义换行，每行一个完整语义片段，便于审查 diff。

跨页引用与标签
--------------

- 标签使用 ``.. _<章节>-<页面>:`` 形式，例如 ``.. _contrib-ci:``，一经发布
  不应随意改名。
- 同章链接使用相对 ``:doc:`` 角色，例如 ``workflow``；跨章链接使用
  ``:ref:`` 加已有标签，例如 ``gs-index``。
- 同一事实只在一个 canonical 页面维护，其他页面链接过去，不复制整段内容。
- 构建会把未解析的引用和重复标签视为错误，因此新增引用前先确认标签存在。

支持状态（延后）
----------------

支持状态（Supported、Experimental、Planned 等状态词、状态列或支持矩阵）整体延后：
本轮文档不添加状态声明、状态列或徽章。页面只描述已经存在的事实能力，例如
"示例使用 single-gpu 机器"，而不判断某项能力是否"受支持"。

构建与检查
----------

首次使用时安装工具链：

.. code-block:: bash

   python3 -m venv docs/.venv
   docs/.venv/bin/pip install -r docs/requirements.txt

日常使用以下命令：

.. code-block:: bash

   just docs          # 严格构建中英文站点（警告视为错误）
   just docs-serve    # 构建后在 http://127.0.0.1:8010/ 预览
   just docs-check    # 构建 + 双语检查 + 生成站点检查

``just docs-check`` 依次执行 ``docs/scripts/build.sh``、
``docs/scripts/check_i18n.py`` 与 ``docs/scripts/verify_build.py``：

- 双语检查：每页在两种语言下都有对应文件、每页都有显式标签、标题层级骨架一致、
  不存在首行语言链接。
- 站点检查：landing 页面存在并跳转到中文站点、每个源文件都生成了 HTML、页面数量
  达到预期、没有残留的迁移占位标记（stub marker）、主题与语言
  切换器已加载。

``.github/workflows/docs.yml`` 在修改 ``docs/**`` 时运行同样的构建与检查；
``main`` 分支的产物发布到 GitHub Pages。

相关页面
--------

- :doc:`workflow`
- :doc:`rust_guidelines`
- :ref:`index`
