---
name: cosim-gpu-disk-image-edit
description: Use when the vHost disk image needs modification without a full rebuild. Mount with guestmount, add files, systemd services, kernel module config.
---

# Cosim Disk Image Edit

Modify a standalone copy of the vHost disk and launch it with an explicit
kernel and disk configuration.

## Prerequisites

- Use a Linux host with `guestmount`, `guestunmount`, `qemu-img` and GNU coreutils.
- Stop processes using the disk before mounting it. Keep the source recipe
  bundle idle while copying its kernel and disk.
- Allow space for a standalone copy of the QCOW2 image (56 GB virtual capacity).

```bash
pgrep -af 'qemu-system-x86_64|cosim_launch.sh|run_cosim_tests.sh' && echo "STOP COSIM FIRST" || echo "OK"
command -v guestmount guestunmount qemu-img timeout tail
```

## Prepare the editable image

Recipe bundles under `build/images/` are verified build artifacts. Preserve
their disk, kernel, manifest and verification records. A `vhost.image`
selection verifies its bundle and rebuilds a modified artifact before launch.

Verify the source bundle, then create a standalone disk and matching kernel in
a new directory under `build/image-edits/`. This directory is ignored by Git.
Use a fresh directory for each edited image; the commands below reject an
existing destination.

```bash
set -euo pipefail
SOURCE_BUNDLE="$PWD/build/images/ubuntu/24.04/x86_64/rocm/7.0"
CUSTOM_DIR="$PWD/build/image-edits/rocm70"
just ci-rocm-assets verify ubuntu/24.04/x86_64/rocm/7.0
test ! -e "$CUSTOM_DIR"
mkdir -p "$CUSTOM_DIR"
cp "$SOURCE_BUNDLE/kernel" "$CUSTOM_DIR/kernel"
qemu-img convert -f qcow2 -O qcow2 "$SOURCE_BUNDLE/disk" "$CUSTOM_DIR/disk.qcow2"
```

Keep the copied kernel paired with the disk's installed kernel modules. Changes
to the kernel require exporting the corresponding boot artifacts as well.

## Mount

```bash
DISK="$CUSTOM_DIR/disk.qcow2"
MOUNTPOINT="$CUSTOM_DIR/mount"
mkdir -p "$MOUNTPOINT"
guestmount -a "$DISK" -i --rw --pid-file "$CUSTOM_DIR/guestmount.pid" "$MOUNTPOINT"
```

## Edit scope

Supported edit classes:

- Add or replace files under the vHost filesystem.
- Add or update systemd units and matching enablement symlinks.
- Add or update kernel module configuration under `/etc/modprobe.d/`.
- Install ROCm runtime debug components through repository scripts when the task is runtime debugging.
- Inspect disk layout with `qemu-img info "$DISK"` if `guestmount` cannot inspect the image.

Keep the concrete file contents in the task artifact or source patch. Do not embed large service templates or generated scripts in the skill itself.

## Unmount

Unmount and wait for the guestmount worker to finish before using the disk.
The timeout must succeed before running any launch command.

```bash
MOUNT_PID="$(cat "$CUSTOM_DIR/guestmount.pid")"
guestunmount "$MOUNTPOINT"
timeout 60s tail --pid="$MOUNT_PID" -f /dev/null
```

The worker completes disk finalization after unmount; see the
[guestmount shutdown contract](https://libguestfs.org/guestmount.1.html#Race-conditions-possible-when-shutting-down-the-connection).

## Launch the edited image

Save this topology as `build/image-edits/rocm70/machine.yaml`. Its vHost uses
the copied kernel and disk directly. Leave `vhost.image` unset so the launcher
does not invoke recipe preparation for this machine.

```yaml
version: 1
imports:
  - vhosts/qemu.yaml
  - devices/gpu/mi300x.yaml
machines:
  - id: m0
    vhost:
      use: vhost-x86
      kernel: build/image-edits/rocm70/kernel
      cmdline: >-
        console=ttyS0 root=/dev/vda1 rw nokaslr modprobe.blacklist=amdgpu
      disks:
        - id: root
          backing: build/image-edits/rocm70/disk.qcow2
          format: qcow2
          bus: virtio
          boot: true
    devices:
      - {use: mi300x}
```

```bash
just run-cli validate build/image-edits/rocm70/machine.yaml --assets
just run-topology build/image-edits/rocm70/machine.yaml --dry-run
just run-topology build/image-edits/rocm70/machine.yaml
```

The session writes an overlay backed by the edited disk. Persist further
offline changes by mounting that edited disk again after its sessions stop.

## Notes

- `guestmount` uses FUSE — no sudo needed
- Offline edits write to the custom QCOW2 disk; the recipe bundle remains intact.
- Keep image edits, the custom topology and mounted paths under the workspace.
