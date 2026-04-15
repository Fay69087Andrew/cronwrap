"""Concurrency guard: limit how many instances of a job run simultaneously."""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


class ConcurrencyLimitError(RuntimeError):
    """Raised when the concurrency limit for a job has been reached."""


@dataclass
class ConcurrencyConfig:
    max_instances: int = 1
    state_dir: str = "/tmp/cronwrap/concurrency"
    enabled: bool = True

    def __post_init__(self) -> None:
        if self.max_instances < 1:
            raise ValueError("max_instances must be >= 1")
        if not self.state_dir:
            raise ValueError("state_dir must not be empty")

    @classmethod
    def from_env(cls) -> "ConcurrencyConfig":
        enabled = os.environ.get("CRONWRAP_CONCURRENCY_ENABLED", "true").lower() != "false"
        max_instances = int(os.environ.get("CRONWRAP_MAX_INSTANCES", "1"))
        state_dir = os.environ.get("CRONWRAP_CONCURRENCY_DIR", "/tmp/cronwrap/concurrency")
        return cls(max_instances=max_instances, state_dir=state_dir, enabled=enabled)


@dataclass
class ConcurrencySlot:
    job_name: str
    pid: int
    acquired_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {"job_name": self.job_name, "pid": self.pid, "acquired_at": self.acquired_at}


def _slot_dir(cfg: ConcurrencyConfig, job_name: str) -> Path:
    return Path(cfg.state_dir) / job_name


def _active_slots(cfg: ConcurrencyConfig, job_name: str) -> list[Path]:
    slot_dir = _slot_dir(cfg, job_name)
    if not slot_dir.exists():
        return []
    live: list[Path] = []
    for p in slot_dir.glob("*.slot"):
        try:
            pid = int(p.stem)
            os.kill(pid, 0)  # check process is alive
            live.append(p)
        except (ValueError, ProcessLookupError, PermissionError):
            try:
                p.unlink(missing_ok=True)
            except OSError:
                pass
    return live


def acquire_slot(cfg: ConcurrencyConfig, job_name: str) -> Optional[Path]:
    """Try to acquire a concurrency slot. Returns slot path on success, None if limit reached."""
    if not cfg.enabled:
        return Path(os.devnull)
    slot_dir = _slot_dir(cfg, job_name)
    slot_dir.mkdir(parents=True, exist_ok=True)
    active = _active_slots(cfg, job_name)
    if len(active) >= cfg.max_instances:
        return None
    slot_path = slot_dir / f"{os.getpid()}.slot"
    slot_path.write_text(str(time.time()))
    return slot_path


def release_slot(slot_path: Optional[Path]) -> None:
    """Release a previously acquired slot."""
    if slot_path is None or slot_path == Path(os.devnull):
        return
    try:
        slot_path.unlink(missing_ok=True)
    except OSError:
        pass


def concurrency_summary(cfg: ConcurrencyConfig, job_name: str) -> dict:
    active = _active_slots(cfg, job_name)
    return {
        "job_name": job_name,
        "max_instances": cfg.max_instances,
        "active_instances": len(active),
        "enabled": cfg.enabled,
    }
