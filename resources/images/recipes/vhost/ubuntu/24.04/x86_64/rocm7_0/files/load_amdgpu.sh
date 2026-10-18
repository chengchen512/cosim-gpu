#!/bin/bash

# Copyright (c) 2025 Advanced Micro Devices, Inc.
# All rights reserved.
# SPDX-License-Identifier: BSD-3-Clause

# The standalone gem5 path uses a minimal ACPI implementation. Load the WMI
# stub and amdgpu dependencies explicitly before loading the driver.
KERNEL_MODULE_ROOT="/lib/modules/$(uname -r)"
DRM_MODULE_ROOT="${KERNEL_MODULE_ROOT}/kernel/drivers/gpu/drm"
DKMS_MODULE_ROOT="${KERNEL_MODULE_ROOT}/updates/dkms"

insmod /home/gem5/gem5_wmi.ko

insmod "${KERNEL_MODULE_ROOT}/kernel/drivers/acpi/video.ko.zst"
insmod "${KERNEL_MODULE_ROOT}/kernel/drivers/i2c/algos/i2c-algo-bit.ko.zst"
insmod "${KERNEL_MODULE_ROOT}/kernel/drivers/media/rc/rc-core.ko.zst"
insmod "${KERNEL_MODULE_ROOT}/kernel/drivers/media/cec/core/cec.ko.zst"
insmod "${DRM_MODULE_ROOT}/display/drm_display_helper.ko.zst"
insmod "${DRM_MODULE_ROOT}/drm_suballoc_helper.ko.zst"
insmod "${DRM_MODULE_ROOT}/drm_exec.ko.zst"
insmod "${DKMS_MODULE_ROOT}/amdkcl.ko.zst"
insmod "${DKMS_MODULE_ROOT}/amd-sched.ko.zst"
insmod "${DKMS_MODULE_ROOT}/amdxcp.ko.zst"
insmod "${DKMS_MODULE_ROOT}/amddrm_buddy.ko.zst"
insmod "${DKMS_MODULE_ROOT}/amddrm_exec.ko.zst"
insmod "${DKMS_MODULE_ROOT}/amdttm.ko.zst"
insmod "${DKMS_MODULE_ROOT}/amddrm_ttm_helper.ko.zst"

AMDGPU_ARGS=(
    ip_block_mask=0x6f
    ppfeaturemask=0
    dpm=0
    audio=0
    ras_enable=0
    discovery=2
)
insmod "${DKMS_MODULE_ROOT}/amdgpu.ko.zst" "${AMDGPU_ARGS[@]}"
