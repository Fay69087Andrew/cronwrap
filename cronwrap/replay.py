"""Replay support for cronwrap.

Allows recording and replaying the last N run results for debugging,
audit, or dry-run comparisons without executing the real command.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class ReplayConfig:
    """Configuration for the replay subsystem."""

    enabled: bool = False
    max_entries: int = 10
    state_dir: str = "/tmp/cronwrap/replay"
    job_id: str = "default"

    def __post_init__(self) -> None:
        if self.max_entries <= 0:
            raise ValueError("max_entries must be a positive integer")
        if not self.state_dir or not self.state_dir.strip():
            raise ValueError("state_dir must not be empty")
        if not self.job_id or not self.job_id.strip():
            raise ValueError("job_id must not be empty")
        self.state_dir = self.state_dir.strip()
        self.job_id = self.job_id.strip()

    @classmethod
    def from_env(cls, env: Optional[dict] = None) -> "ReplayConfig":
        """Build a ReplayConfig from environment variables.

        Recognised variables:
          CRONWRAP_REPLAY_ENABLED     – '1' / 'true' to enable
          CRONWRAP_REPLAY_MAX_ENTRIES – integer (default 10)
          CRONWRAP_REPLAY_STATE_DIR   – directory path
          CRONWRAP_REPLAY_JOB_ID      – logical job identifier
        """
        e = env if env is not None else os.environ
        raw_enabled = e.get("CRONWRAP_REPLAY_ENABLED", "false").lower()
        enabled = raw_enabled in ("1", "true", "yes")
        max_entries = int(e.get("CRONWRAP_REPLAY_MAX_ENTRIES", "10"))
        state_dir = e.get("CRONWRAP_REPLAY_STATE_DIR", "/tmp/cronwrap/replay")
        job_id = e.get("CRONWRAP_REPLAY_JOB_ID", "default")
        return cls(
            enabled=enabled,
            max_entries=max_entries,
            state_dir=state_dir,
            job_id=job_id,
        )


@dataclass
class ReplayEntry:
    """A single recorded run result suitable for replay."""

    job_id: str
    command: str
    exit_code: int
    stdout: str
    stderr: str
    recorded_at: float = field(default_factory=time.time)

    def succeeded(self) -> bool:
        return self.exit_code == 0

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "command": self.command,
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "recorded_at": self.recorded_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ReplayEntry":
        return cls(
            job_id=data["job_id"],
            command=data["command"],
            exit_code=data["exit_code"],
            stdout=data["stdout"],
            stderr=data["stderr"],
            recorded_at=data.get("recorded_at", 0.0),
        )


class ReplayStore:
    """Persists and retrieves ReplayEntry records for a given job."""

    def __init__(self, config: ReplayConfig) -> None:
        self._config = config
        self._path = Path(config.state_dir) / f"{config.job_id}.json"

    def _load(self) -> List[dict]:
        if not self._path.exists():
            return []
        try:
            return json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []

    def _save(self, records: List[dict]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(records, indent=2), encoding="utf-8")

    def record(self, entry: ReplayEntry) -> None:
        """Append *entry* to the store, pruning to max_entries."""
        records = self._load()
        records.append(entry.to_dict())
        records = records[-self._config.max_entries :]
        self._save(records)

    def latest(self) -> Optional[ReplayEntry]:
        """Return the most recently recorded entry, or None."""
        records = self._load()
        if not records:
            return None
        return ReplayEntry.from_dict(records[-1])

    def all(self) -> List[ReplayEntry]:
        """Return all stored entries in chronological order."""
        return [ReplayEntry.from_dict(r) for r in self._load()]

    def clear(self) -> None:
        """Remove all stored replay entries for this job."""
        if self._path.exists():
            self._path.unlink()
