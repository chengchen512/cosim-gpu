# SPDX-License-Identifier: Apache-2.0

from contextlib import contextmanager
import os
import select
import signal
import subprocess
import threading
from typing import Iterator


class Lifecycle:
    def __init__(self, input_fd: int | None = None):
        self.input_fd = input_fd
        self.reason: str | None = None
        self.process: subprocess.Popen | None = None
        self.closed = threading.Event()

    def request(self, reason: str) -> None:
        if self.reason is None:
            self.reason = reason
        process = self.process
        if process is not None and process.poll() is None:
            process.terminate()

    def check(self) -> None:
        if self.reason is not None:
            raise RuntimeError(self.reason)

    @contextmanager
    def own(self, process: subprocess.Popen) -> Iterator[None]:
        self.process = process
        if self.reason is not None:
            self.request(self.reason)
        try:
            yield
        finally:
            self.process = None

    def watch_input(self) -> None:
        assert self.input_fd is not None
        while not self.closed.is_set():
            try:
                ready, _, _ = select.select([self.input_fd], [], [], 0.2)
                if ready and not os.read(self.input_fd, 4096):
                    self.request("container input closed")
                    return
            except OSError as error:
                if not self.closed.is_set():
                    self.request(f"input lifeline failed: {error}")
                return

    def handle_signal(self, number: int, _frame: object) -> None:
        self.request(f"received {signal.Signals(number).name}")

    @contextmanager
    def installed(self) -> Iterator["Lifecycle"]:
        previous = {
            number: signal.signal(number, self.handle_signal)
            for number in (signal.SIGINT, signal.SIGTERM)
        }
        watcher = None
        if self.input_fd is not None:
            watcher = threading.Thread(target=self.watch_input, daemon=True)
            watcher.start()
        try:
            yield self
        finally:
            self.closed.set()
            if watcher is not None:
                watcher.join(timeout=1)
            for number, handler in previous.items():
                signal.signal(number, handler)
