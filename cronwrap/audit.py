"""Audit log: records every cronwrap execution to a newline-delimited JSON file."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from cronwrap.runner import RunResult


@dataclass
class AuditConfig:
    enabled: bool = True
    audit_dir: Path = Path(os.environ.get("CRONWRAP_AUDIT_DIR", "/var/log/cronwrap/audit"))
    max_entries: int = 10_000

    def __post_init__(self) -> None:
        self.audit_dir = Path(self.audit_dir)
        if self.max_entries < 1:
            raise ValueError("max_entries must be at least 1")

    @classmethod
    def from_env(cls) -> "AuditConfig":
        return cls(
            enabled=os.environ.get("CRONWRAP_AUDIT_ENABLED", "true").lower() != "false",
            audit_dir=Path(os.environ.get("CRONWRAP_AUDIT_DIR", "/var/log/cronwrap/audit")),
            max_entries=int(os.environ.get("CRONWRAP_AUDIT_MAX_ENTRIES", "10000")),
        )


@dataclass
class AuditEntry:
    job_name: str
    command: str
    exit_code: int
    stdout: str
    stderr: str
    started_at: datetime
    finished_at: datetime
    attempt: int = 1
    tags: List[str] = field(default_factory=list)

    @property
    def succeeded(self) -> bool:
        return self.exit_code == 0

    @property
    def duration_seconds(self) -> float:
        return (self.finished_at - self.started_at).total_seconds()

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "command": self.command,
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat(),
            "duration_seconds": self.duration_seconds,
            "attempt": self.attempt,
            "tags": self.tags,
            "succeeded": self.succeeded,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AuditEntry":
        return cls(
            job_name=data["job_name"],
            command=data["command"],
            exit_code=data["exit_code"],
            stdout=data["stdout"],
            stderr=data["stderr"],
            started_at=datetime.fromisoformat(data["started_at"]),
            finished_at=datetime.fromisoformat(data["finished_at"]),
            attempt=data.get("attempt", 1),
            tags=data.get("tags", []),
        )


class AuditStore:
    def __init__(self, config: AuditConfig) -> None:
        self.config = config

    def _audit_file(self, job_name: str) -> Path:
        self.config.audit_dir.mkdir(parents=True, exist_ok=True)
        safe = job_name.replace(os.sep, "_").replace(" ", "_")
        return self.config.audit_dir / f"{safe}.audit.jsonl"

    def record(self, entry: AuditEntry) -> None:
        if not self.config.enabled:
            return
        path = self._audit_file(entry.job_name)
        lines: List[str] = []
        if path.exists():
            lines = path.read_text().splitlines()
        lines.append(json.dumps(entry.to_dict()))
        if len(lines) > self.config.max_entries:
            lines = lines[-self.config.max_entries :]
        path.write_text("\n".join(lines) + "\n")

    def read(self, job_name: str) -> List[AuditEntry]:
        path = self._audit_file(job_name)
        if not path.exists():
            return []
        entries = []
        for line in path.read_text().splitlines():
            line = line.strip()
            if line:
                entries.append(AuditEntry.from_dict(json.loads(line)))
        return entries
