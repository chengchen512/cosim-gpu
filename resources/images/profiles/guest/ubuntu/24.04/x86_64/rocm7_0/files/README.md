<!--
SPDX-License-Identifier: Apache-2.0
-->

# vHost image inputs

This directory holds the ROCm vHost profile's guest scripts, WMI module source
and serial console override. The profile's `profile.toml` lists every build
input and the shared Ansible tasks copy the selected files into the guest.

The MI200 and MI300 option ROMs and MI300/MI350 discovery firmware are read
from the pinned `third_party/gem5-resources` submodule. Their content is
fingerprinted as part of the image profile inputs.

The `gem5_wmi/` workaround retains its BSD-3-Clause license and copyright
notice. `run_gem5_app.sh` and `load_amdgpu.sh` retain their upstream copyright
and BSD-3-Clause notices. The AMD BSD-3-Clause license is installed in the
guest at `/usr/share/doc/cosim-gpu-image/LICENSE.BSD-3-Clause`. The serial
console override is maintained in this profile and uses the systemd-provided
`agetty` service.
