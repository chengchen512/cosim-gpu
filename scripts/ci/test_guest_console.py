# SPDX-License-Identifier: Apache-2.0

import unittest

import pexpect

from guest_console import GuestConsole


class GuestConsoleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.shell = pexpect.spawn(
            "/bin/bash", ["--noprofile", "--norc"], echo=False
        )
        self.console = GuestConsole(self.shell)

    def tearDown(self) -> None:
        self.shell.close(force=True)

    def test_output_cannot_replace_a_successful_exit(self) -> None:
        result = self.console.run("printf '[PASS] result (1 ms)\\n'; exit 7", 5)
        self.assertEqual(result.exit_code, 7)
        with self.assertRaisesRegex(RuntimeError, "exited with 7"):
            result.require_workload("result")

    def test_timeout_is_a_failure_even_after_output(self) -> None:
        result = self.console.run(
            "printf '[PASS] result (1 ms)\\n'; "
            "timeout --kill-after=1 0.2 sleep 10", 5
        )
        self.assertEqual(result.exit_code, 124)
        with self.assertRaisesRegex(RuntimeError, "exited with 124"):
            result.require_workload("result")

    def test_success_without_numerical_result_fails(self) -> None:
        result = self.console.run("printf 'workload did not run\\n'", 5)
        with self.assertRaisesRegex(RuntimeError, "missing numerical result"):
            result.require_workload("result")

    def test_incomplete_command_cannot_pass(self) -> None:
        with self.assertRaises(pexpect.TIMEOUT):
            self.console.run("sleep 10", 0.2)

    def test_result_and_completion_are_both_required(self) -> None:
        result = self.console.run("printf '[PASS] result (1 ms)\\n'", 5)
        result.require_workload("result")
        next_result = self.console.run("printf 'next command\\n'; exit 9", 5)
        self.assertEqual(next_result.exit_code, 9)
        self.assertNotIn(b"[PASS]", next_result.output)


if __name__ == "__main__":
    unittest.main()
