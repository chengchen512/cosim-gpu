<!--
SPDX-License-Identifier: BSD-3-Clause
-->

# gem5 WMI/ACPI workaround module

Starting around ROCm 6.0, the amdgpu ROCk driver's Kconfig enables the WMI ACPI extensions whenever ACPI is enabled. This is a problem for Linux 6.x kernels: the display manager code makes ACPI calls related to backlight features. gem5 does not have enough ACPI support for the WMI kernel module to load. Earlier ROCm versions on Linux 5.x did not have this issue because the `acpi_video` module loaded when ACPI was disabled. The WMI kernel module fails to load when ACPI is disabled, which also prevents the amdgpu kernel module from loading.

This module implements a WMI stub that allows the `acpi_video` module to load. This is suitable for simulating compute GPUs, which disable the display manager IP block.

The module requires the Linux kernel source. The image profile installs the matching `linux-headers-$(uname -r)` package and builds the module for the selected kernel.

## Build the module

The image profile builds this module. To build it manually, run:

```bash
make -C "/lib/modules/$(uname -r)/build" M="$PWD"
```

The command creates `gem5_wmi.ko` in this directory.
