# SPDX-License-Identifier: Apache-2.0

from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[2]
ASSIGNER_SCRIPT = ROOT / "scripts" / "ci" / "set_assignees.py"


class SetAssigneesImportTests(unittest.TestCase):
    def test_help_loads_maintainer_module_from_host_scripts(self):
        result = subprocess.run(
            [sys.executable, str(ASSIGNER_SCRIPT), "--help"],
            cwd=ROOT,
            capture_output=True,
            check=False,
            text=True,
            timeout=30,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Assign maintainers", result.stdout)
