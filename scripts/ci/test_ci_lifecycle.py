# SPDX-License-Identifier: Apache-2.0

import os
import signal
import subprocess
import unittest

from ci_lifecycle import Lifecycle


class LifecycleTests(unittest.TestCase):
    def test_signal_terminates_the_owned_process(self) -> None:
        with Lifecycle().installed() as lifecycle:
            with subprocess.Popen(["cat"], stdin=subprocess.PIPE) as process:
                with lifecycle.own(process):
                    os.kill(os.getpid(), signal.SIGTERM)
                    self.assertEqual(process.wait(timeout=5), -signal.SIGTERM)
                self.assertEqual(lifecycle.reason, "received SIGTERM")

    def test_input_eof_terminates_the_owned_process(self) -> None:
        reader, writer = os.pipe()
        try:
            with Lifecycle(reader).installed() as lifecycle:
                with subprocess.Popen(
                    ["cat"], stdin=subprocess.PIPE
                ) as process:
                    with lifecycle.own(process):
                        os.close(writer)
                        writer = -1
                        self.assertEqual(
                            process.wait(timeout=5), -signal.SIGTERM
                        )
                    self.assertEqual(lifecycle.reason, "container input closed")
        finally:
            os.close(reader)
            if writer >= 0:
                os.close(writer)

    def test_cancellation_before_registration_is_delivered(self) -> None:
        with Lifecycle().installed() as lifecycle:
            os.kill(os.getpid(), signal.SIGINT)
            with subprocess.Popen(["cat"], stdin=subprocess.PIPE) as process:
                with lifecycle.own(process):
                    self.assertEqual(process.wait(timeout=5), -signal.SIGTERM)
            with self.assertRaisesRegex(RuntimeError, "SIGINT"):
                lifecycle.check()


if __name__ == "__main__":
    unittest.main()
