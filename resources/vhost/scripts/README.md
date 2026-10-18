<!--
SPDX-License-Identifier: Apache-2.0
-->

# Shared vHost scripts

Store vHost scripts shared by multiple image recipes in this directory. Image-specific scripts belong in a recipe's `files/` directory and are registered as recipe inputs so the image identity includes their content. Ansible installs those files into the vHost OS.

Host automation belongs in `scripts/host/`; GitHub Actions helpers and tests belong in `scripts/ci/`. A CI payload that executes inside a vHost belongs with the image recipe that defines that vHost OS.
