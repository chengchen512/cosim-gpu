# SPDX-License-Identifier: Apache-2.0

import os
from pathlib import Path
import signal
import shutil
import subprocess
import tempfile
import threading
import time
import unittest

from ci_lifecycle import Lifecycle
from rocm_assets import install_copies, qemu_binary, run_logged
from runtime_artifact import ROOT, sha256


class ImageProcessTests(unittest.TestCase):
    def test_cancel_stops_descendant_without_newline_and_keeps_output(self):
        with tempfile.TemporaryDirectory() as name:
            directory = Path(name)
            pid_file = directory / "child.pid"

            def cancel_after_start():
                deadline = time.monotonic() + 5
                while not pid_file.exists() and time.monotonic() < deadline:
                    time.sleep(0.02)
                os.kill(os.getpid(), signal.SIGTERM)

            with Lifecycle().installed() as lifecycle:
                sender = threading.Thread(target=cancel_after_start)
                sender.start()
                started = time.monotonic()
                with self.assertRaisesRegex(RuntimeError, "SIGTERM"):
                    run_logged([
                        "bash", "-c", 'sleep 30 & child=$!; printf ready; '
                        'printf "%s" "$child" > "$1/child.pid"; wait',
                        "image-command", str(directory),
                    ], directory, lifecycle)
                sender.join()
                self.assertLess(time.monotonic() - started, 5)
            child = int(pid_file.read_text())
            deadline = time.monotonic() + 5
            while (Path(f"/proc/{child}").exists()
                   and time.monotonic() < deadline):
                time.sleep(0.02)
            self.assertFalse(Path(f"/proc/{child}").exists())
            self.assertIn(b"ready", (directory / "build.log").read_bytes())

    def test_writable_install_is_independent_and_preserves_existing_files(self):
        source = ROOT / "LICENSE"
        original = sha256(source)
        with tempfile.TemporaryDirectory() as name:
            destination = Path(name) / "installed"
            install_copies({source: destination})
            self.assertEqual(sha256(destination), original)
            self.assertFalse(os.path.samefile(source, destination))
            destination.write_bytes(b"local changes\n")
            self.assertEqual(sha256(source), original)
            with self.assertRaises(FileExistsError):
                install_copies({source: destination})
            self.assertEqual(destination.read_bytes(), b"local changes\n")
            self.assertEqual(list(Path(name).iterdir()), [destination])

    def test_explicit_qemu_selects_real_binary_and_rejects_missing_path(self):
        selected = shutil.which("qemu-system-x86_64")
        self.assertIsNotNone(selected)
        previous = os.environ.get("QEMU_BIN")
        try:
            os.environ["QEMU_BIN"] = selected
            binary = qemu_binary()
            self.assertEqual(binary, Path(selected).resolve())
            subprocess.run([str(binary), "--version"], check=True,
                           stdout=subprocess.DEVNULL)
            with tempfile.TemporaryDirectory() as name:
                os.environ["QEMU_BIN"] = str(Path(name) / "missing-qemu")
                with self.assertRaisesRegex(RuntimeError, "QEMU_BIN"):
                    qemu_binary()
        finally:
            if previous is None:
                os.environ.pop("QEMU_BIN", None)
            else:
                os.environ["QEMU_BIN"] = previous


if __name__ == "__main__":
    unittest.main()
