# SPDX-License-Identifier: Apache-2.0

import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import tempfile
import time
import unittest
import uuid

import yaml

from ci_lifecycle import Lifecycle
from run_rocm import Inputs, archive, stop, topology
from runtime_artifact import ROOT


class LauncherLifecycleTests(unittest.TestCase):
    def test_rocm_plan_respects_runner_budget_and_external_parameters(self):
        launcher = Path(os.environ.get("CARGO_TARGET_DIR", ROOT / "target"))
        launcher = launcher / "release/cosim"
        session_parent = ROOT / ".cosim"
        session_parent.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(
            dir=session_parent, prefix="ci-plan-"
        ) as name:
            directory = Path(name)
            for options, budget in (({}, 8 << 30), (
                {"memory": "3G", "vram": "2G", "cpus": 1}, 5 << 30
            )):
                with self.subTest(options=options):
                    inputs = Inputs(
                        output=directory, assets=directory, launcher=launcher,
                        gem5=ROOT / "gem5/build/x86_64/VEGA_X86/gem5.opt",
                        qemu=ROOT / "qemu/build/qemu-system-x86_64",
                        boot_timeout=300, test_timeout=300, **options,
                    )
                    config = directory / "topology.yaml"
                    config.write_text(yaml.safe_dump(
                        topology(inputs, directory, "qcow2")
                    ))
                    plan = json.loads(subprocess.check_output([
                        str(launcher), "plan", str(config),
                        "--run-dir", str(directory / "run"),
                    ]))
                    self.assertLessEqual(
                        plan["machines"][0]["memory"]["size"], budget
                    )
                    host = next(p for p in plan["processes"]
                                if p["role"] == "host")
                    argv = host["argv"]
                    self.assertEqual(
                        argv[argv.index("-smp") + 1], str(inputs.cpus)
                    )

    def exercise(self, close_input: bool) -> None:
        launcher = Path(os.environ.get("CARGO_TARGET_DIR", ROOT / "target"))
        launcher = launcher / "release/cosim"
        profile = "tcg-aarch64" if platform.machine() == "aarch64" else "tcg"
        output = ROOT / "artifacts/ci-check" / uuid.uuid4().hex[:8]
        output.mkdir(parents=True)
        session_parent = ROOT / ".cosim"
        session_parent.mkdir(exist_ok=True)
        reader, writer = os.pipe()
        try:
            with tempfile.TemporaryDirectory(
                dir=session_parent, prefix="ci-test-"
            ) as name:
                directory = Path(name)
                session = directory / "run"
                pool = directory / "pool"
                pid_file = directory / "qemu.pid"
                config = directory / "topology.yaml"
                config.write_text(yaml.safe_dump({
                    "version": 1,
                    "imports": [str(ROOT / "samples/hosts" / path) for path in
                                ("qemu.yaml", f"{profile}.yaml")],
                    "machines": [{"id": "m0", "host": {
                        "use": profile,
                        "args": [
                            "-S", "-nodefaults", "-pidfile", str(pid_file)
                        ],
                    }}],
                }))
                log_path = output / "launcher.log"
                with Lifecycle(reader).installed() as lifecycle:
                    with log_path.open("wb") as log:
                        process = subprocess.Popen([
                            str(launcher), "run", str(config), "--run-dir",
                            str(session), "--pool-dir", str(pool),
                            "--stdin-lifeline", "--ready-timeout", "15",
                        ], stdin=subprocess.PIPE, stdout=log,
                            stderr=subprocess.STDOUT)
                        with lifecycle.own(process):
                            try:
                                deadline = time.monotonic() + 20
                                while (
                                    b"ready: m0.host"
                                    not in log_path.read_bytes()
                                ):
                                    if process.poll() is not None:
                                        self.fail(log_path.read_text())
                                    if time.monotonic() >= deadline:
                                        self.fail("QEMU readiness timed out")
                                    time.sleep(0.05)
                                pid = int(pid_file.read_text())
                                if close_input:
                                    os.close(writer)
                                    writer = -1
                                else:
                                    os.kill(os.getpid(), signal.SIGTERM)
                                self.assertEqual(process.wait(timeout=20), 0)
                            finally:
                                try:
                                    stop(process, session)
                                finally:
                                    archive(session, output)
                with self.assertRaises(ProcessLookupError):
                    os.kill(pid, 0)
                self.assertFalse(pool.exists())
                verdict = json.loads(
                    (output / "session/verdict.json").read_text()
                )
                self.assertEqual(verdict["status"], "PASS")
                self.assertTrue(verdict["users_stopped"])
                self.assertEqual(verdict["cleanup_errors"], [])
                host_log = output / "session/m0/host/output.log"
                self.assertTrue(host_log.exists())
        finally:
            os.close(reader)
            if writer >= 0:
                os.close(writer)

    def test_terminated_runner_cleans_qemu_and_keeps_evidence(self) -> None:
        self.exercise(close_input=False)

    def test_closed_input_cleans_qemu_and_keeps_evidence(self) -> None:
        self.exercise(close_input=True)


if __name__ == "__main__":
    unittest.main()
