from __future__ import annotations

import subprocess
from typing import Any


class ProcessLauncher:
    """Launch an actual vendor process if a pinned start command exists."""

    kind = "ACTUAL"

    def __init__(self, start_command: list[str] | None, cwd: str | None = None):
        self.start_command = start_command
        self.cwd = cwd
        self.proc: subprocess.Popen | None = None

    def start(self) -> subprocess.Popen:
        if not self.start_command:
            raise RuntimeError("MISSING_START_COMMAND")
        self.proc = subprocess.Popen(self.start_command, cwd=self.cwd)
        return self.proc

    def stop(self) -> None:
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
