# SPDX-License-Identifier: Apache-2.0

import subprocess
import unittest

import yaml

from run_rocm import PROGRAMS, VHOST_REGRESSION_SCRIPT
from runtime_artifact import ROOT
from resources.images.profile import load_profile


class GuestBuildTargetTests(unittest.TestCase):
    def test_guest_build_directory_matches_the_makefile_targets(self):
        script = (
            ROOT / "resources/images/profiles/guest/ubuntu/24.04/x86_64/"
            "rocm7_0/files/cosim_rocm_regression.sh"
        ).read_text()
        self.assertIn('make -j1 "BUILDDIR=build" "build/$program"', script)
        for program in PROGRAMS:
            with self.subTest(program=program):
                result = subprocess.run(
                    [
                        "make", "--question", "-C", str(ROOT / "tests"),
                        "BUILDDIR=build", f"build/{program}",
                    ],
                    capture_output=True, text=True, check=False,
                )
                self.assertIn(
                    result.returncode,
                    (0, 1),
                    f"make could not resolve build/{program}: {result.stderr}",
                )

    def test_vhost_scripts_are_image_inputs(self):
        profile = load_profile(
            ROOT, "guest/ubuntu/24.04/x86_64/rocm7_0"
        )
        tasks = yaml.safe_load(
            profile.tasks_file.read_text(encoding="utf-8")
        )
        install_task = next(
            task for task in tasks if task["name"] == "Install image inputs"
        )
        destinations = {
            item["source"]: item["destination"]
            for item in install_task["loop"]
        }
        expected = {
            "vhost_gpu_setup": "/usr/local/bin/cosim-gpu-setup.sh",
            "vhost_rocm_regression": VHOST_REGRESSION_SCRIPT,
        }
        for input_name, destination in expected.items():
            with self.subTest(input_name=input_name):
                script = profile.inputs[input_name]
                self.assertTrue(script.is_file())
                self.assertEqual(script.parent, profile.directory / "files")
                source = f"{{{{ cosim_inputs.{input_name} }}}}"
                self.assertEqual(destinations[source], destination)

    def test_serial_console_override_is_installed_for_ttyS0(self):
        profile = load_profile(
            ROOT, "guest/ubuntu/24.04/x86_64/rocm7_0"
        )
        tasks = yaml.safe_load(
            profile.tasks_file.read_text(encoding="utf-8")
        )
        install_task = next(
            task for task in tasks if task["name"] == "Install image inputs"
        )
        override_input = "{{ cosim_inputs.serial_getty_override }}"
        override = next(
            item for item in install_task["loop"]
            if item["source"] == override_input
        )

        self.assertEqual(
            override["destination"],
            "/etc/systemd/system/serial-getty@ttyS0.service.d/override.conf",
        )
        content = profile.inputs["serial_getty_override"].read_text()
        self.assertIn("ExecStart=\n", content)
        self.assertIn("--autologin root", content)

    def test_amd_bsd_license_is_installed_in_the_guest(self):
        profile = load_profile(
            ROOT, "guest/ubuntu/24.04/x86_64/rocm7_0"
        )
        tasks = yaml.safe_load(
            profile.tasks_file.read_text(encoding="utf-8")
        )
        install_task = next(
            task for task in tasks if task["name"] == "Install image inputs"
        )
        license_input = "{{ cosim_inputs.amd_bsd_license }}"
        destinations = {
            item["source"]: item["destination"]
            for item in install_task["loop"]
        }

        self.assertEqual(
            destinations[license_input],
            "/usr/share/doc/cosim-gpu-image/LICENSE.BSD-3-Clause",
        )
        self.assertTrue(profile.inputs["amd_bsd_license"].is_file())

    def test_amdgpu_dkms_is_pinned_to_the_verified_package(self):
        profile = load_profile(
            ROOT, "guest/ubuntu/24.04/x86_64/rocm7_0"
        )
        tasks = yaml.safe_load(
            profile.tasks_file.read_text(encoding="utf-8")
        )
        install_task = next(
            task for task in tasks
            if task["name"] == "Install the AMDGPU and ROCm stack"
        )

        self.assertEqual(
            profile.variables["amdgpu_dkms_version"],
            "1:6.14.14.30100000-2204008.24.04",
        )
        self.assertIn(
            "amdgpu-dkms={{ cosim_profile_variables.amdgpu_dkms_version }}",
            install_task["ansible.builtin.apt"]["name"],
        )

    def test_dkms_failure_path_prints_logs_and_fails_the_build(self):
        profile = load_profile(
            ROOT, "guest/ubuntu/24.04/x86_64/rocm7_0"
        )
        tasks = yaml.safe_load(
            profile.tasks_file.read_text(encoding="utf-8")
        )
        dkms_task = next(
            task for task in tasks
            if task["name"]
            == "Build the AMDGPU DKMS module for the selected kernel"
        )

        log_task = next(
            task for task in dkms_task["rescue"]
            if task["name"] == "Print AMDGPU DKMS build logs"
        )
        failure_task = dkms_task["rescue"][-1]

        self.assertEqual(
            log_task["ansible.builtin.command"]["argv"],
            ["cat", "{{ item.path }}"],
        )
        self.assertEqual(
            log_task["loop"], "{{ amdgpu_dkms_logs.files | default([]) }}"
        )
        self.assertIs(log_task["changed_when"], True)
        self.assertEqual(
            failure_task["name"], "Report AMDGPU DKMS build failure"
        )
        self.assertIn("ansible.builtin.fail", failure_task)
