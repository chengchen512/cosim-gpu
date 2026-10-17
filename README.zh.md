<p align="center">
  <strong>简体中文</strong> ·
  <a href="README.md">English</a>
</p>

<div align="center">
  <h1 align="center">Cosim-GPU</h1>
  <p><strong>使用 QEMU 和 gem5 进行 YAML 配置的 AMD MI300X GPU 联合仿真</strong></p>
</div>

<p align="center">
  <img alt="Linux x86_64 与 ARM64" src="https://img.shields.io/badge/Linux-x86%5F64%20%7C%20ARM64-FCC624?logo=linux&amp;logoColor=black">
  <img alt="Rust 1.95+" src="https://img.shields.io/badge/Rust-1.95%2B-orange?logo=rust&amp;logoColor=white">
  <img alt="QEMU 设备模型" src="https://img.shields.io/badge/QEMU-vfio--user-FF6600">
  <img alt="gem5 MI300X" src="https://img.shields.io/badge/gem5-MI300X-6f42c1">
  <img alt="ROCm HIP" src="https://img.shields.io/badge/ROCm-HIP-ED1C24">
  <img alt="Apache 2.0 许可证" src="https://img.shields.io/badge/license-Apache--2.0-34a853">
</p>

<p align="center">
  <a href="docs/zh/getting-started.md">快速入门</a> ·
  <a href="docs/zh/topology.md">拓扑参考</a> ·
  <a href="docs/zh/architecture.md">架构说明</a>
</p>

使用 YAML 描述 Linux 宿主机和模拟设备，再通过 Rust <code>cosim</code>
启动器创建会话。宿主 QEMU 通过 **vfio-user** 连接 gem5 或 QEMU 设备进程。
gem5 MI300X 模型可在 Linux 客户机中运行 AMD ROCm/HIP 负载。

## 🧭 架构

~~~mermaid
flowchart LR
    YAML[拓扑 YAML] --> CLI[Rust cosim 启动器]

    subgraph Linux 宿主机
        CLI --> H[宿主 QEMU]
        CLI --> G[gem5 MI300X 进程]
        CLI --> Q[QEMU 设备进程]
        H <-->|vfio-user| G
        H <-->|vfio-user| Q
        H --- P[机器内存池]
        G --- P
        Q --- P
        H --> Guest[Linux 客户机 · ROCm/HIP]
    end
~~~

启动器校验配置，计算客户机内存和设备区域偏移，准备磁盘 overlay，并管理进程与会话
资源。设备通信和模拟器时序由设备模型负责。

## 🚀 快速入门

~~~bash
just submodules
just dev-image        # 非 Linux 主机，或设置 COSIM_ENV=container

# 构建工具链和客户机镜像流程，然后启动示例机器
just build-all
just run samples/machines/single-gpu.yaml
~~~

查看拓扑配置，不启动模拟器：

~~~bash
just cosim validate samples/machines/gpu-8.yaml
just cosim plan samples/machines/mixed-models.yaml
just cosim graph samples/clusters/cluster-4x8.yaml
~~~

### 🧪 拓扑示例

- 🎮 <code>samples/machines/single-gpu.yaml</code>：启动单 GPU 客户机。
- 🔀 <code>samples/machines/mixed-models.yaml</code>：组合 gem5 和 QEMU 设备模型。
- 🧮 <code>samples/machines/gpu-8.yaml</code>：查看八 GPU 机器及其 96 GiB 内存池。
- 🐧 <code>samples/machines/host-only-aarch64.yaml</code>：在 ARM64 上检查仅含宿主机的配置。

<details>
<summary>示例：一台机器组合 gem5 和 QEMU 设备</summary>

~~~yaml
version: 1
imports:
  - hosts/qemu.yaml
  - hosts/ubuntu-24.yaml
  - devices/gpu/mi300x.yaml
  - devices/pci/qemu-edu.yaml
machines:
  - id: m0
    host: {use: ubuntu, memory: 32G}
    devices:
      - {use: mi300x, count: 2}
      - {use: qemu-edu}
~~~

QEMU 设备示例使用 <code>just build-qemu</code> 构建的 QEMU，通过
<code>x-vfio-user-server</code> 提供真实的 <code>edu</code> PCI 模型。

</details>

## 🖥️ 宿主机与构建环境

### 🦀 启动器和配置工具

使用 Rust 1.95+、Cargo 和 just，也可以在开发容器中运行这些 recipe。

构建 QEMU、gem5、m5 和 <code>cosim</code>，运行拓扑以及执行 Rust 检查的 recipe
通过 <code>scripts/dev.sh</code> 执行。非 Linux 系统或设置
<code>COSIM_ENV=container</code> 时，这些 recipe 会在基于
<code>scripts/Dockerfile.dev</code> 构建的临时容器中运行。源码树会挂载到容器中，
命令退出后容器随即删除。客户机镜像、HIP 应用构建以及 shell 接口
（<code>just launch</code> 和 <code>just test</code>）使用各自的 Docker 和主机流程。

### 🐧 Linux 宿主机运行会话

- 需要 glibc 和 util-linux 提供的 <code>setpriv</code>。
- 需要匹配宿主机架构的 QEMU 和 <code>qemu-img</code>。
- x86_64 使用 <code>qemu-system-x86_64</code>；ARM64 使用
  <code>qemu-system-aarch64</code>。
- <code>COSIM_HOST_ARCH</code> 用于选择构建架构，默认使用当前宿主机架构。
  gem5 在 x86_64 上构建到 <code>build/x86_64/VEGA_X86</code>，在 ARM64 上构建到
  <code>build/aarch64/VEGA_X86</code>。

### 🎮 MI300X 和 QEMU 设备模型

- MI300X 联合仿真需要 gem5 VEGA_X86、支持 vfio-user 的 QEMU、客户机镜像输入，
  以及 Ubuntu 客户机所需的 KVM。
- QEMU 设备服务端需要使用 <code>--enable-vfio-user-server</code> 构建。
- 提供的 Ubuntu/ROCm 客户机镜像构建流程面向 x86_64。
- 客户机镜像和模拟器产物需要足够的磁盘空间。内存池所在文件系统必须容纳完整的机器布局。

## ⌨️ 常用命令

### 🔎 检查拓扑

~~~bash
just cosim validate samples/machines/gpu-8.yaml
just cosim plan samples/machines/mixed-models.yaml
just cosim graph samples/clusters/cluster-4x8.yaml
~~~

### 🏗️ 构建

- <code>just dev-image</code> 构建开发容器镜像。
- <code>just dev-shell</code> 在临时容器中打开 shell。
- <code>just build-all</code> 构建完整项目流程和客户机镜像。
- <code>just build-cosim</code> 构建 release 版本的启动器。
- <code>just build-qemu [jobs]</code> 构建支持 KVM 和 vfio-user 的 QEMU。
- <code>just build-gem5 [jobs]</code> 构建 gem5；链接时内存不足可使用一个任务。
- <code>just build-disk</code> 构建 Ubuntu/ROCm 客户机镜像。

### ▶️ 启动和测试

- <code>just run &lt;yaml&gt;</code> 启动拓扑。
- <code>just run-dev &lt;yaml&gt;</code> 使用开发版本启动拓扑。
- <code>just launch [options]</code> 运行基于 shell 的 QEMU/gem5 接口。
- <code>just test --all</code> 在全新会话中运行客户机 GPU 测试。
- <code>just check-cosim</code> 运行 rustfmt、Clippy 和 Rust 测试。
- <code>just test-cosim-integration</code> 使用真实 QEMU 进程、磁盘和信号运行会话。
- <code>just test-cosim-vfio-user</code> 在集成会话中加入 QEMU vfio-user 设备。

使用已安装的 QEMU 检查仅含宿主机的配置：

~~~bash
just run-dev samples/machines/host-only.yaml --run-for 1
just run-dev samples/machines/host-only-aarch64.yaml --run-for 1
~~~

会话目录包含解析后的执行计划、内存布局、进程日志和
<code>verdict.json</code>。客户机驱动由 <code>cosim-gpu-setup.service</code> 初始化，
参数如下：

~~~text
amdgpu ip_block_mask=0x67 ppfeaturemask=0 dpm=0 audio=0 ras_enable=0 discovery=2
~~~

## 🗂️ 仓库目录

- 🦀 **Rust 工作区**
  - <code>crates/cosim-topology/</code> 负责 YAML 文档、校验类型、内存布局和适配器渲染。
  - <code>crates/cosim-runtime/</code> 负责执行计划、会话资源、进程监督和清理。
  - <code>crates/cosim-cli/</code> 提供 <code>cosim</code> 命令行接口。
- 🧪 **模拟器模型**
  - <code>gem5/</code> 包含 MI300X 模型和 vfio-user 接口。
  - <code>qemu/</code> 包含宿主 QEMU 和 QEMU 设备服务端实现。
  - <code>gem5-resources/</code> 包含客户机镜像、内核和 GPU 程序。
  - <code>configs/sst/</code> 包含 SST 网络拓扑和集成实验。
- 🧰 **项目工具**
  - <code>samples/</code> 包含宿主机、设备、机器和集群配置。
  - <code>scripts/</code> 与 <code>justfile</code> 包含构建 recipe、开发容器和客户机测试工具。
  - <code>.agents/</code> 包含仓库工作流。

## 📚 文档

- [拓扑与运行管理](docs/zh/topology.md)
- [快速入门](docs/zh/getting-started.md)
- [架构说明](docs/zh/architecture.md)
- [Rust 开发规范](docs/zh/guidelines.md)
- [参考手册](docs/zh/reference.md)
- [贡献指南](docs/zh/contributing.md)

顶层项目使用 [Apache 2.0 许可证](LICENSE)。子模块保留各自的许可证。
