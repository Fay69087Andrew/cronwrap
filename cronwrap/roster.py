"""Job roster — tracks which jobs are registered and their metadata."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class RosterConfig:
    enabled: bool = True
    state_dir: str = "/tmp/cronwrap/roster"
    max_jobs: int = 256

    def __post_init__(self) -> None:
        if self.max_jobs <= 0:
            raise ValueError("max_jobs must be a positive integer")
        if not self.state_dir:
            raise ValueError("state_dir must not be empty")

    @classmethod
    def from_env(cls) -> "RosterConfig":
        return cls(
            enabled=os.environ.get("CRONWRAP_ROSTER_ENABLED", "true").lower() == "true",
            state_dir=os.environ.get("CRONWRAP_ROSTER_STATE_DIR", "/tmp/cronwrap/roster"),
            max_jobs=int(os.environ.get("CRONWRAP_ROSTER_MAX_JOBS", "256")),
        )


@dataclass
class RosterEntry:
    job_id: str
    command: str
    registered_at: float = field(default_factory=time.time)
    last_seen: Optional[float] = None
    tags: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "command": self.command,
            "registered_at": self.registered_at,
            "last_seen": self.last_seen,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RosterEntry":
        return cls(
            job_id=data["job_id"],
            command=data["command"],
            registered_at=data.get("registered_at", 0.0),
            last_seen=data.get("last_seen"),
            tags=data.get("tags", {}),
        )


class RosterStore:
    def __init__(self, cfg: RosterConfig) -> None:
        self._cfg = cfg
        self._path = Path(cfg.state_dir)

    def _entry_path(self, job_id: str) -> Path:
        return self._path / f"{job_id}.json"

    def register(self, entry: RosterEntry) -> None:
        if not self._cfg.enabled:
            return
        self._path.mkdir(parents=True, exist_ok=True)
        existing = self.list_jobs()
        if entry.job_id not in {e.job_id for e in existing} and len(existing) >= self._cfg.max_jobs:
            raise RuntimeError(f"Roster is full (max_jobs={self._cfg.max_jobs})")
        self._entry_path(entry.job_id).write_text(json.dumps(entry.to_dict()))

    def get(self, job_id: str) -> Optional[RosterEntry]:
        p = self._entry_path(job_id)
        if not p.exists():
            return None
        return RosterEntry.from_dict(json.loads(p.read_text()))

    def touch(self, job_id: str) -> None:
        entry = self.get(job_id)
        if entry:
            entry.last_seen = time.time()
            self.register(entry)

    def deregister(self, job_id: str) -> None:
        p = self._entry_path(job_id)
        if p.exists():
            p.unlink()

    def list_jobs(self) -> List[RosterEntry]:
        if not self._path.exists():
            return []
        return [RosterEntry.from_dict(json.loads(p.read_text())) for p in self._path.glob("*.json")]
