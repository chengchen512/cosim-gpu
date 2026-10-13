[English](../en/contributing.md)

# 贡献指南

本文规定 cosim-gpu 顶层仓库的补丁要求。`gem5` 和 `gem5-resources` 子模块中的修改遵守对应仓库的规则。

## 补丁检查要求

提交到 cosim-gpu 的每个非合并提交都必须通过 `scripts/checkpatch.pl` 检查，且不能出现错误。该脚本来自 QEMU 的 `scripts/checkpatch.pl`，cosim-gpu 采用它所检查的 QEMU 补丁风格：

- 每个提交都带有 `Signed-off-by:` 行，格式必须为 `Signed-off-by: Name <email>`，姓名和电子邮件地址取自 `git config user.name` 和 `git config user.email`。
- 提交信息中不能出现标注 AI 的附加字段，例如标注 AI 工具的 `Co-authored-by:` 行、`Assisted-by:`、`Generated-by:` 或 `🤖` 标记。
- 新增的行不能包含行尾空白、DOS 换行符或无效的 UTF-8 字符。文件以换行符结尾。
- 源文件（`.c`、`.h`、`.cpp`、`.py`、`.sh`、`.pl` 等）使用空格缩进。超过 80 列的行产生警告，超过 90 列的行产生错误。
- 声明解释器的 Python 脚本使用 `python3`。
- C 和 C++ 代码（`.c`、`.h`、`.cpp`）遵守 QEMU 编码风格：使用 `/* */` 注释，`if`/`else` 的所有分支都加花括号，指针写作 `type *name`，函数的左花括号单独占一行。
- 新增源文件以 `SPDX-License-Identifier:` 行开头，不能复制许可证模板文本。项目许可证为 `Apache-2.0`；来自 `MIT`、`BSD-2-Clause`、`BSD-3-Clause` 许可证源码的代码可以使用这些许可证，并在提交信息中说明原因。

错误会使检查失败。警告会被报告，但不会使检查失败；提交前需要逐条确认警告。

检查范围是提交新增或修改的行。提交修改已有代码时，被修改的部分同样接受检查。

## 在本地运行检查

检查当前分支上尚未进入 `origin/main` 的全部提交：

```bash
git fetch origin
./scripts/check_patch.sh
```

检查指定版本之后的提交：

```bash
./scripts/check_patch.sh <base-commit>
```

`scripts/check_patch.sh` 只输出存在问题的提交，每条报告以提交哈希和补丁行号开头；任一提交出现错误时，脚本以非零状态退出。

其他输入可以直接使用 `scripts/checkpatch.pl` 检查：

```bash
# 单个提交或提交范围
./scripts/checkpatch.pl HEAD
./scripts/checkpatch.pl origin/main..HEAD

# git format-patch 生成的补丁文件
./scripts/checkpatch.pl 0001-example.patch

# 检查整个文件（不检查 Signed-off-by）
./scripts/checkpatch.pl -f scripts/cosim_launch.sh
```

`scripts/checkpatch.pl` 需要 Perl 5，并且必须在 cosim-gpu 源码树中运行。

## 持续集成

`.github/workflows/ci.yml` 中的 `Checkpatch` 任务在每个指向 `main` 的拉取请求和每次推送到 `main` 时运行 `scripts/check_patch.sh`：

| 事件 | 检查的提交 |
|------|------------|
| 拉取请求 | `<PR 基准提交>..<PR 头部提交>` |
| 推送到 `main` | `<推送前的 main 提交>..<推送后的 main 提交>` |
| 推送时没有之前的提交 | 推送的最新提交 |

任务失败时会阻止拉取请求合并。修正报告中的行，修改或变基相关提交，然后强制推送分支。

## 与 QEMU checkpatch.pl 的差异

`scripts/checkpatch.pl` 复制自 QEMU 提交 `615ece3c406b262996e569f29ea6eed0d81c4d8d`，并包含以下 cosim-gpu 修改：

| 方面 | cosim-gpu 行为 |
|------|----------------|
| 源码树识别 | 识别 cosim-gpu 根目录（`LICENSE`、`README.md`、`agents.md`、`.gitmodules`、`docs`、`scripts`、`tests`） |
| SPDX 许可证 | 首选 `Apache-2.0`；同时接受 `MIT`、`BSD-2-Clause`、`BSD-3-Clause` |
| SPDX 要求 | 新增的 `.cpp` 和 `.hpp` 文件同样必须包含 `SPDX-License-Identifier` |
| 许可证模板 | 新文件中出现 Apache License 模板文本时报告错误 |
| 消息文本 | 错误信息指向 cosim-gpu |

其他检查与 QEMU 保持一致。针对 QEMU 专有路径的检查（例如 `linux-headers/`、ACPI 测试数据和 `trace-events` 文件）不会匹配 cosim-gpu 的路径。

该脚本保留上游的 GPL-2.0 许可证。它是开发工具，不会编译进联合仿真程序，也不会随联合仿真程序分发。

从 QEMU 更新该脚本时，复制新的上游 `scripts/checkpatch.pl`，重新应用上表中的修改，并更新本节记录的 QEMU 提交。

## 误报

`scripts/checkpatch.pl` 对正确代码报告错误时，在 cosim-gpu 仓库提交问题，附上对应提交和完整报告。
