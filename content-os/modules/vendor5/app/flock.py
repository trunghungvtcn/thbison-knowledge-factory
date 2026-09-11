from __future__ import annotations

try:
    import fcntl
except ImportError:  # Windows lab runner
    fcntl = None
    import msvcrt
from pathlib import Path


class InterprocessLock:
    def __init__(self, path: str | Path):
        self.path = Path(str(path) + ".lock")
        self._fp = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fp = open(self.path, "a+", encoding="utf-8")
        if fcntl is not None:
            fcntl.flock(self._fp.fileno(), fcntl.LOCK_EX)
        else:
            self._fp.seek(0)
            self._fp.write("0")
            self._fp.flush()
            self._fp.seek(0)
            msvcrt.locking(self._fp.fileno(), msvcrt.LK_LOCK, 1)
        return self

    def __exit__(self, *exc):
        if self._fp:
            if fcntl is not None:
                fcntl.flock(self._fp.fileno(), fcntl.LOCK_UN)
            else:
                self._fp.seek(0)
                msvcrt.locking(self._fp.fileno(), msvcrt.LK_UNLCK, 1)
            self._fp.close()
            self._fp = None
