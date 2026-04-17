"""Snapshot: capture and compare job output digests across runs."""
from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SnapshotConfig:
    enabled: bool = False
    state_dir: str = "/tmp/cronwrap/snapshots"
    algorithm: str = "sha256"

    def __post_init__(self) -> None:
        self.algorithm = self.algorithm.lower()
        if self.algorithm not in hashlib.algorithms_guaranteed:
            raise ValueError(f"Unsupported hash algorithm: {self.algorithm}")
        if not self.state_dir:
            raise ValueError("state_dir must not be empty")

    @classmethod
    def from_env(cls) -> "SnapshotConfig":
        return cls(
            enabled=os.environ.get("CRONWRAP_SNAPSHOT_ENABLED", "").lower() == "true",
            state_dir=os.environ.get("CRONWRAP_SNAPSHOT_DIR", "/tmp/cronwrap/snapshots"),
            algorithm=os.environ.get("CRONWRAP_SNAPSHOT_ALGO", "sha256"),
        )


@dataclass
class Snapshot:
    job: str
    digest: str
    captured_at: float = field(default_factory=time.time)
    changed: bool = False

    def to_dict(self) -> dict:
        return {
            "job": self.job,
            "digest": self.digest,
            "captured_at": self.captured_at,
            "changed": self.changed,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Snapshot":
        return cls(
            job=d["job"],
            digest=d["digest"],
            captured_at=d["captured_at"],
            changed=d["changed"],
        )


class SnapshotStore:
    def __init__(self, config: SnapshotConfig) -> None:
        self.config = config
        Path(config.state_dir).mkdir(parents=True, exist_ok=True)

    def _path(self, job: str) -> Path:
        safe = job.replace("/", "_").replace(" ", "_")
        return Path(self.config.state_dir) / f"{safe}.json"

    def _digest(self, text: str) -> str:
        h = hashlib.new(self.config.algorithm)
        h.update(text.encode("utf-8", errors="replace"))
        return h.hexdigest()

    def record(self, job: str, output: str) -> Snapshot:
        digest = self._digest(output)
        previous = self.load(job)
        changed = previous is None or previous.digest != digest
        snap = Snapshot(job=job, digest=digest, changed=changed)
        self._path(job).write_text(json.dumps(snap.to_dict()))
        return snap

    def load(self, job: str) -> Snapshot | None:
        p = self._path(job)
        if not p.exists():
            return None
        return Snapshot.from_dict(json.loads(p.read_text()))

    def clear(self, job: str) -> None:
        p = self._path(job)
        if p.exists():
            p.unlink()
