<!--
SPDX-License-Identifier: Apache-2.0
-->

# Cosim-GPU Domain Context

This glossary defines the runtime environments and accelerator model boundary used throughout cosim-gpu.

## Runtime environments

**Host（宿主机环境）**: The operating-system environment that runs the Rust launcher, Host-side QEMU and Device Model processes. The Host can be Linux directly or the configured development container.
_Avoid_: guest host, QEMU host

**vHost（虚拟 Host 环境）**: The virtual host environment created by QEMU using KVM or TCG. It boots the selected vHost OS image and provides the virtual hardware used by workloads.
_Avoid_: guest OS, virtual machine host

**Host-side QEMU（Host 侧 QEMU）**: The QEMU process running on the Host that creates the vHost and presents Device Model PCI functions to its operating system.
_Avoid_: QEMU host

## Accelerator models

**Device Model（设备模型）**: An independent process on the Host that represents a selected vGPU or vGPGPU target and exposes its PCI function through the vfio-user interface backed by libvfio-user.
_Avoid_: in-process GPU model

**vGPU / vGPGPU**: The simulated GPU target represented by a Device Model and presented to the vHost as a PCI device.
_Avoid_: physical GPU, passthrough GPU
