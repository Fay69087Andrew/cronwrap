"""Throttle: skip a job run if it completed successfully within a minimum interval."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

_DEFAULT_STATE_DIR = "/tmp/cronwrap/throttle"
_DEFAULT_MIN_INTERVAL = 0  # seconds; 0 means no throttling


@dataclass
class ThrottleConfig:
    min_interval: int = _DEFAULT_MIN_INTERVAL  # seconds
    state_dir: str = _DEFAULT_STATE_DIR
    enabled: bool = True

    def __post_init__(self) -> None:
        if self.min_interval < 0:
            raise ValueError("min_interval must be >= 0")
        if not self.state_dir:
            raise ValueError("state_dir must not be empty")

    @classmethod
    def from_env(cls) -> "ThrottleConfig":
        enabled = os.environ.get("CRONWRAP_THROTTLE_ENABLED", "true").lower() != "false"
        raw_interval = os.environ.get("CRONWRAP_THROTTLE_MIN_INTERVAL", str(_DEFAULT_MIN_INTERVAL))
        state_dir = os.environ.get("CRONWRAP_THROTTLE_STATE_DIR", _DEFAULT_STATE_DIR)
        return cls(
            min_interval=int(raw_interval),
            state_dir=state_dir,
            enabled=enabled,
        )


@dataclass
class ThrottleState:
    job_id: str
    last_success_ts: Optional[float] = None

    def to_dict(self) -> dict:
        return {"job_id": self.job_id, "last_success_ts": self.last_success_ts}

    @classmethod
    def from_dict(cls, data: dict) -> "ThrottleState":
        return cls(job_id=data["job_id"], last_success_ts=data.get("last_success_ts"))


def _state_path(cfg: ThrottleConfig, job_id: str) -> Path:
    safe = job_id.replace("/", "_").replace(" ", "_")
    return Path(cfg.state_dir) / f"{safe}.json"


def load_state(cfg: ThrottleConfig, job_id: str) -> ThrottleState:
    path = _state_path(cfg, job_id)
    if path.exists():
        with path.open() as fh:
            return ThrottleState.from_dict(json.load(fh))
    return ThrottleState(job_id=job_id)


def save_state(cfg: ThrottleConfig, state: ThrottleState) -> None:
    path = _state_path(cfg, state.job_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as fh:
        json.dump(state.to_dict(), fh)


def should_throttle(cfg: ThrottleConfig, state: ThrottleState) -> bool:
    """Return True if the job should be skipped (ran successfully too recently)."""
    if not cfg.enabled or cfg.min_interval == 0:
        return False
    if state.last_success_ts is None:
        return False
    elapsed = time.time() - state.last_success_ts
    return elapsed < cfg.min_interval


def record_success(cfg: ThrottleConfig, job_id: str) -> ThrottleState:
    """Persist a successful run timestamp for *job_id* and return the updated state."""
    state = ThrottleState(job_id=job_id, last_success_ts=time.time())
    save_state(cfg, state)
    return state
