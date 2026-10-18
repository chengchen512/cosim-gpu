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
