"""Lockfile support to prevent overlapping cron job executions."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


class LockFileError(Exception):
    """Raised when a lock cannot be acquired."""


@dataclass
class LockConfig:
    lock_dir: str = "/tmp/cronwrap"
    enabled: bool = True

    def __post_init__(self) -> None:
        self.lock_dir = str(self.lock_dir)

    @classmethod
    def from_env(cls) -> "LockConfig":
        enabled = os.environ.get("CRONWRAP_LOCK_ENABLED", "true").lower() != "false"
        lock_dir = os.environ.get("CRONWRAP_LOCK_DIR", "/tmp/cronwrap")
        return cls(lock_dir=lock_dir, enabled=enabled)


@dataclass
class LockFile:
    job_name: str
    config: LockConfig = field(default_factory=LockConfig)
    _path: Optional[Path] = field(default=None, init=False, repr=False)

    def _lock_path(self) -> Path:
        safe_name = self.job_name.replace("/", "_").replace(" ", "_")
        return Path(self.config.lock_dir) / f"{safe_name}.lock"

    def acquire(self) -> None:
        """Create the lockfile; raise LockFileError if already locked."""
        if not self.config.enabled:
            return
        lock_path = self._lock_path()
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        if lock_path.exists():
            try:
                pid = int(lock_path.read_text().strip())
            except ValueError:
                pid = None
            raise LockFileError(
                f"Job '{self.job_name}' is already running (lock: {lock_path}, pid: {pid})"
            )
        lock_path.write_text(str(os.getpid()))
        self._path = lock_path

    def release(self) -> None:
        """Remove the lockfile if it was acquired by this instance."""
        if not self.config.enabled:
            return
        if self._path and self._path.exists():
            self._path.unlink()
            self._path = None

    def __enter__(self) -> "LockFile":
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.release()
        return None
