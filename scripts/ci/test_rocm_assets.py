# SPDX-License-Identifier: Apache-2.0

from pathlib import Path
import tempfile
import unittest

from rocm_assets import find_m5_binary


class M5BuildPathTests(unittest.TestCase):
    def test_prefers_the_workspace_build_output(self):
        with tempfile.TemporaryDirectory() as name:
            workspace = Path(name)
            source = workspace / "gem5-resources/recipe"
            central = workspace / "build/m5/x86/out/m5"
            legacy = source / "files/m5"
            central.parent.mkdir(parents=True)
            central.write_bytes(b"central m5")
            legacy.parent.mkdir(parents=True)
            legacy.write_bytes(b"legacy m5")

            self.assertEqual(find_m5_binary(workspace, source), central)

    def test_falls_back_to_an_existing_resource_m5_binary(self):
        with tempfile.TemporaryDirectory() as name:
            workspace = Path(name)
            source = workspace / "gem5-resources/recipe"
            legacy = source / "files/m5"
            legacy.parent.mkdir(parents=True)
            legacy.write_bytes(b"legacy m5")

            self.assertEqual(find_m5_binary(workspace, source), legacy)

    def test_returns_none_when_neither_m5_binary_exists(self):
        with tempfile.TemporaryDirectory() as name:
            workspace = Path(name)
            source = workspace / "gem5-resources/recipe"

            self.assertIsNone(find_m5_binary(workspace, source))
