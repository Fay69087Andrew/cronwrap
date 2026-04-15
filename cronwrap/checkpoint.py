"""Checkpoint support: persist and restore job progress markers."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class CheckpointConfig:
    enabled: bool = False
    state_dir: str = "/tmp/cronwrap/checkpoints"
    ttl_seconds: int = 86400  # 24 hours

    def __post_init__(self) -> None:
        if self.ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        if not self.state_dir:
            raise ValueError("state_dir must not be empty")

    @classmethod
    def from_env(cls) -> "CheckpointConfig":
        enabled = os.environ.get("CRONWRAP_CHECKPOINT_ENABLED", "false").lower() == "true"
        state_dir = os.environ.get("CRONWRAP_CHECKPOINT_DIR", "/tmp/cronwrap/checkpoints")
        ttl = int(os.environ.get("CRONWRAP_CHECKPOINT_TTL", "86400"))
        return cls(enabled=enabled, state_dir=state_dir, ttl_seconds=ttl)


@dataclass
class Checkpoint:
    job_id: str
    data: Dict[str, Any] = field(default_factory=dict)
    saved_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {"job_id": self.job_id, "data": self.data, "saved_at": self.saved_at}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Checkpoint":
        return cls(job_id=d["job_id"], data=d.get("data", {}), saved_at=d.get("saved_at", 0.0))

    def is_expired(self, ttl_seconds: int) -> bool:
        return (time.time() - self.saved_at) > ttl_seconds


class CheckpointStore:
    def __init__(self, cfg: CheckpointConfig) -> None:
        self._cfg = cfg
        if cfg.enabled:
            Path(cfg.state_dir).mkdir(parents=True, exist_ok=True)

    def _path(self, job_id: str) -> Path:
        safe = job_id.replace("/", "_").replace(" ", "_")
        return Path(self._cfg.state_dir) / f"{safe}.json"

    def save(self, job_id: str, data: Dict[str, Any]) -> Checkpoint:
        cp = Checkpoint(job_id=job_id, data=data)
        if self._cfg.enabled:
            self._path(job_id).write_text(json.dumps(cp.to_dict()))
        return cp

    def load(self, job_id: str) -> Optional[Checkpoint]:
        if not self._cfg.enabled:
            return None
        p = self._path(job_id)
        if not p.exists():
            return None
        cp = Checkpoint.from_dict(json.loads(p.read_text()))
        if cp.is_expired(self._cfg.ttl_seconds):
            p.unlink(missing_ok=True)
            return None
        return cp

    def clear(self, job_id: str) -> None:
        if self._cfg.enabled:
            self._path(job_id).unlink(missing_ok=True)
