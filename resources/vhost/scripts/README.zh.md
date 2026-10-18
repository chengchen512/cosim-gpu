<!--
SPDX-License-Identifier: Apache-2.0
-->

# vHost 通用脚本

供多个镜像配方共同使用的 vHost 脚本放在此目录。只供某个镜像使用的脚本放在该配方的 `files/` 目录，并登记为配方输入，使镜像身份包含脚本内容。Ansible 会将这些文件安装到 vHost 操作系统。

Host 自动化脚本放在 `scripts/host/`；GitHub Actions 辅助程序和测试放在 `scripts/ci/`。在 vHost 内执行的 CI 脚本放在定义该 vHost 操作系统的镜像配方中。
