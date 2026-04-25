"""Periodic digest reporting: batch run results and emit a summary on a schedule."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional


@dataclass
class DigestConfig:
    enabled: bool = False
    state_dir: str = "/tmp/cronwrap/digest"
    max_entries: int = 100
    job_name: str = "default"

    def __post_init__(self) -> None:
        if not isinstance(self.enabled, bool):
            raise TypeError("enabled must be a bool")
        if not self.state_dir or not self.state_dir.strip():
            raise ValueError("state_dir must not be empty")
        if self.max_entries <= 0:
            raise ValueError("max_entries must be a positive integer")
        if not self.job_name or not self.job_name.strip():
            raise ValueError("job_name must not be empty")
        self.job_name = self.job_name.strip()

    @classmethod
    def from_env(cls) -> "DigestConfig":
        enabled_raw = os.environ.get("CRONWRAP_DIGEST_ENABLED", "false").lower()
        return cls(
            enabled=enabled_raw in ("1", "true", "yes"),
            state_dir=os.environ.get("CRONWRAP_DIGEST_STATE_DIR", "/tmp/cronwrap/digest"),
            max_entries=int(os.environ.get("CRONWRAP_DIGEST_MAX_ENTRIES", "100")),
            job_name=os.environ.get("CRONWRAP_DIGEST_JOB_NAME", "default"),
        )


@dataclass
class DigestEntry:
    job_name: str
    command: str
    exit_code: int
    duration: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def succeeded(self) -> bool:
        return self.exit_code == 0

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "command": self.command,
            "exit_code": self.exit_code,
            "duration": self.duration,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DigestEntry":
        return cls(
            job_name=data["job_name"],
            command=data["command"],
            exit_code=data["exit_code"],
            duration=data["duration"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )


class DigestStore:
    def __init__(self, cfg: DigestConfig) -> None:
        self._cfg = cfg
        self._path = Path(cfg.state_dir) / f"{cfg.job_name}.digest.json"

    def _load(self) -> List[dict]:
        if not self._path.exists():
            return []
        try:
            return json.loads(self._path.read_text())
        except (json.JSONDecodeError, OSError):
            return []

    def record(self, entry: DigestEntry) -> None:
        entries = self._load()
        entries.append(entry.to_dict())
        entries = entries[-self._cfg.max_entries:]
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(entries, indent=2))

    def entries(self) -> List[DigestEntry]:
        return [DigestEntry.from_dict(d) for d in self._load()]

    def clear(self) -> None:
        if self._path.exists():
            self._path.unlink()

    def summary(self) -> dict:
        all_entries = self.entries()
        if not all_entries:
            return {"total": 0, "passed": 0, "failed": 0, "success_rate": 0.0}
        passed = sum(1 for e in all_entries if e.succeeded())
        failed = len(all_entries) - passed
        return {
            "total": len(all_entries),
            "passed": passed,
            "failed": failed,
            "success_rate": round(passed / len(all_entries) * 100, 1),
        }
