# SPDX-License-Identifier: Apache-2.0

import subprocess
import unittest

from run_rocm import PROGRAMS
from runtime_artifact import ROOT


class GuestBuildTargetTests(unittest.TestCase):
    def test_guest_build_directory_matches_the_makefile_targets(self):
        script = (ROOT / "scripts/ci/rocm_guest.sh").read_text()
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
