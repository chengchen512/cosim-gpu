# QEMU + gem5 MI300X 联合仿真

[English](README.md)

将 **QEMU**（KVM 加速的宿主机 CPU/系统仿真）与 **gem5**（周期精确的 MI300X GPU
模型）相结合的联合仿真框架，无需物理 GPU 硬件即可运行真实的 AMD ROCm/HIP 工作负载。

```
+-----------------------------+       +----------------------------+
|  QEMU  (Q35 + KVM)          |       |  gem5  (Docker)            |
|  +-----------------------+  |       |  +----------------------+  |
|  | Guest Linux           |  |       |  | MI300X GPU Model     |  |
|  | amdgpu driver         |  |       |  |  Shader / CU / SDMA  |  |
|  | ROCm 7.0 / HIP        |  |       |  |  PM4 / Ruby caches   |  |
|  +----------+------------+  |       |  +---------+------------+  |
|  +----------v------------+  |       |  +---------v------------+  |
|  | vfio-user-pci         |<-------->|  | MI300XVfioUser       |  |
|  | (QEMU built-in)       |  |vfio-  |  | (libvfio-user)       |  |
|  +-----------------------+  |user   |  +----------------------+  |
+-----------------------------+       +----------------------------+
        |                                       |
        v                                       v
  /dev/shm/cosim-guest-ram            /dev/shm/mi300x-vram
  (shared guest RAM)                  (shared GPU VRAM)
```

## 功能特性

- **完整驱动加载** — amdgpu DRM 初始化，7 个 XCP 分区，gfx942 架构
- **HIP 计算验证** — hipMalloc、内核调度、hipDeviceSynchronize 全流程通过
- **MSI-X 中断转发** — gem5 → QEMU 中断转发，IH ring buffer 正常工作
- **共享内存 DMA** — 通过 `/dev/shm` 实现 VRAM 和 Guest RAM 的零拷贝共享
- **驱动自动加载** — systemd 服务自动以 `ip_block_mask=0x67 discovery=2` 加载

## 前置条件

| 需求 | 说明 |
|---|---|
| 宿主机系统 | Linux x86_64，支持 KVM（已在 WSL2 6.6.x 验证） |
| Docker | 守护进程运行中，当前用户在 `docker` 组 |
| KVM | `/dev/kvm` 可访问 |
| QEMU | 由 `qemu` 子模块编译（`just build-qemu`），或使用系统安装且提供 `vfio-user-pci` 的 QEMU 10.1+ |
| just | [just](https://github.com/casey/just) 1.27+ 任务运行工具 |
| 磁盘空间 | 约 120 GB（55G 磁盘镜像 + 构建中间产物） |
| 内存 | 建议 16 GB 以上 |

## 快速开始

### 方案 A：使用 just

```bash
git clone --recurse-submodules git@github.com:gevico/cosim-gpu.git
cd cosim-gpu

# 构建 recipe 在容器中运行时（非 Linux 系统，或设置 COSIM_ENV=container），
# 先构建开发镜像
just dev-image

# 构建 QEMU、gem5、m5、磁盘镜像和 square 程序
#（总计约 2 小时，需要 KVM + Docker + 约 60GB 磁盘空间）
just build-all

# 启动联合仿真
just launch
```

运行 `just` 可以列出全部任务。常用任务：

| 任务 | 用途 |
|---|---|
| `just dev-image` | 根据 `scripts/Dockerfile.dev` 构建开发容器镜像 |
| `just build-gem5 [jobs]` | 在 Linux 主机或开发容器中编译 gem5（链接阶段内存不足时使用 `just build-gem5 1`） |
| `just build-disk` | 构建 Guest 磁盘镜像和内核 |
| `just launch [选项]` | 启动 QEMU + gem5；选项传给 `scripts/cosim_launch.sh` |
| `just test <过滤条件>` / `just test --all` | 在新的仿真会话中运行 Guest GPU 测试 |
| `just status` | 显示已有的构建产物 |
| `just check` | 运行 checkpatch、ShellCheck 和 MAINTAINERS.yml 检查 |

### 方案 B：手动分步构建

```bash
# 1. 克隆仓库（含子模块）
git clone --recurse-submodules git@github.com:gevico/cosim-gpu.git
cd cosim-gpu

# 2. 从 qemu 子模块编译 QEMU（gevico/qemu 的 gevico/cosim-gpu 分支）
cd qemu
./configure --target-list=x86_64-softmmu --enable-kvm --disable-docs
make -j"$(nproc)"
./build/qemu-system-x86_64 -device help | grep vfio-user-pci
cd ..

# 3. 构建开发镜像（包含 gem5 编译依赖，以及 ext/libvfio-user 编译所需的 json-c）
docker build -t cosim-dev:local -f scripts/Dockerfile.dev scripts

# 4. 编译 gem5（Docker 内，约 30 分钟；链接阶段 OOM 可改用 -j1）
cd gem5
docker run --rm -v "$(pwd):/gem5" -w /gem5 \
    cosim-dev:local \
    scons build/VEGA_X86/gem5.opt -j4
cd ..

# 5. 预编译 m5 工具（推荐 - 避免构建磁盘镜像时在 Guest 内 git clone）
docker run --rm -v "$(pwd)/gem5:/gem5" -w /gem5 \
    cosim-dev:local \
    bash -c "cd util/m5 && scons build/x86/out/m5"
cp gem5/util/m5/build/x86/out/m5 gem5-resources/src/x86-ubuntu-gpu-ml/files/

# 6. 构建磁盘镜像（Ubuntu 24.04 + ROCm 7.0，约 40 分钟，需要 KVM + 约 60GB 磁盘空间）
./scripts/run_mi300x_fs.sh build-disk

# 7. 启动联合仿真
./scripts/cosim_launch.sh
```

Guest 启动后（自动以 root 登录），GPU 驱动通过 `cosim-gpu-setup.service`
自动加载（约 40 秒）。验证：

```bash
rocm-smi          # 应显示设备 0x74a0
rocminfo          # 应显示 gfx942

# 手动加载（如果 systemd 服务未安装）：
dd if=/root/roms/mi300.rom of=/dev/mem bs=1k seek=768 count=128
modprobe amdgpu ip_block_mask=0x67 ppfeaturemask=0 dpm=0 audio=0 ras_enable=0 discovery=2

# 运行 HIP 测试
cat > /tmp/test.cpp << 'EOF'
#include <hip/hip_runtime.h>
#include <cstdio>
__global__ void add(int *a, int *b, int *c, int n) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n) c[i] = a[i] + b[i];
}
int main() {
    const int N = 4;
    int ha[] = {1,2,3,4}, hb[] = {10,20,30,40}, hc[4] = {};
    int *da, *db, *dc;
    hipMalloc(&da, N*4); hipMalloc(&db, N*4); hipMalloc(&dc, N*4);
    hipMemcpy(da, ha, N*4, hipMemcpyHostToDevice);
    hipMemcpy(db, hb, N*4, hipMemcpyHostToDevice);
    add<<<1, N>>>(da, db, dc, N);
    hipMemcpy(hc, dc, N*4, hipMemcpyDeviceToHost);
    printf("Result: %d %d %d %d\n", hc[0], hc[1], hc[2], hc[3]);
    printf("%s\n", (hc[0]==11&&hc[1]==22&&hc[2]==33&&hc[3]==44) ? "PASSED!" : "FAILED!");
    hipFree(da); hipFree(db); hipFree(dc);
}
EOF
/opt/rocm/bin/hipcc --offload-arch=gfx942 -o /tmp/test /tmp/test.cpp
/tmp/test
# 预期输出: Result: 11 22 33 44
#           PASSED!
```

## 仓库结构

```
cosim-gpu/
|-- qemu/                    # QEMU (submodule, gevico/cosim-gpu branch, v11.1.2)
|-- gem5/                    # gem5 simulator (submodule, gevico/cosim-gpu branch)
|   |-- src/dev/amdgpu/      # MI300X GPU device model & vfio-user bridge
|   |-- ext/libvfio-user/    # libvfio-user library (Nutanix)
|   `-- configs/example/gpufs/mi300_cosim.py  # cosim configuration
|-- gem5-resources/          # disk images, kernels, GPU apps (submodule)
|-- .agents/                 # 可复用的仓库工作流（已内置）
|-- scripts/                 # build & launch scripts
|   |-- cosim_launch.sh      # one-click cosim launcher
|   |-- run_mi300x_fs.sh     # build orchestration
|   |-- cosim_guest_setup.sh # guest-side GPU setup
|   |-- checkpatch.pl        # patch style checker (from QEMU)
|   |-- get_maintainer.py    # MAINTAINERS.yml lookup (from Zephyr)
|   |-- ci/                  # reviewer assignment for GitHub Actions
|   |-- build.sh             # QEMU、gem5 和 m5 的构建步骤
|   |-- dev.sh               # 在主机或临时容器中运行命令
|   `-- Dockerfile.dev       # 开发容器镜像
|-- docs/                    # technical documentation (zh + en)
|   |-- en/                  # English
|   `-- zh/                  # Chinese
|-- justfile                 # task runner entry point (`just --list`)
|-- MAINTAINERS.yml          # areas, maintainers and review assignment
|-- LICENSE                  # Apache 2.0
`-- README.md
```

## 技术文档

详细技术文档位于 [`docs/`](docs/README.md) 目录下：

- [快速入门](docs/zh/getting-started.md) — 从编译到运行首个 HIP 测试的全流程
- [架构文档](docs/zh/architecture.md) — 系统设计、内存共享、地址翻译
- [参考手册](docs/zh/reference.md) — 参数表、故障排查、调试命令
- [贡献指南](docs/zh/contributing.md) — 补丁要求、checkpatch 检查与维护者审查

## 版本矩阵

| 组件 | 版本 |
|---|---|
| Guest 操作系统 | Ubuntu 24.04.2 LTS |
| Guest 内核 | 6.8.0-79-generic |
| ROCm | 7.0.0 |
| GPU 设备 | MI300X (gfx942, DeviceID 0x74A0) |
| gem5 构建目标 | VEGA_X86, GPU_VIPER 一致性协议 |

## 许可证

本项目采用 [Apache License 2.0](LICENSE) 许可证。

注意：各子模块（QEMU、gem5、gem5-resources）遵循各自的许可证。

## 致谢

- [gem5](https://www.gem5.org/) — 模块化计算机体系结构仿真器
- [QEMU](https://www.qemu.org/) — 开源机器模拟器
- [ROCm](https://rocm.docs.amd.com/) — AMD GPU 计算平台
