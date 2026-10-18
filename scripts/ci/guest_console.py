# SPDX-License-Identifier: Apache-2.0

from dataclasses import dataclass
import re
import uuid

from pexpect.spawnbase import SpawnBase


@dataclass(frozen=True)
class CommandResult:
    exit_code: int
    output: bytes

    def require_success(self) -> None:
        if self.exit_code != 0:
            raise RuntimeError(f"vHost command exited with {self.exit_code}")

    def require_workload(self, name: str) -> None:
        self.require_success()
        marker = rb"(?m)^\[PASS\] " + re.escape(name.encode()) + rb" \("
        if re.search(marker, self.output) is None:
            raise RuntimeError(f"missing numerical result for {name}")


class GuestConsole:
    def __init__(self, transport: SpawnBase):
        self.transport = transport

    def run(self, command: str, timeout: float) -> CommandResult:
        token = "COSIM_DONE_" + uuid.uuid4().hex
        self.transport.sendline(
            f"printf '\\n'; ( {command} ); _cosim_rc=$?; "
            f"printf '\\n%s=%s\\n' '{token}' \"$_cosim_rc\"".encode()
        )
        self.transport.expect(
            rb"\r?\n" + token.encode() + rb"=([0-9]+)\r?\n", timeout=timeout
        )
        return CommandResult(
            int(self.transport.match.group(1)), self.transport.before
        )
