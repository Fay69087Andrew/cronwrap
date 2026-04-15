"""Run quota enforcement — limit how many times a job may run in a time window."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List


class QuotaExceededError(Exception):
    """Raised when a job has exhausted its run quota."""


@dataclass
class QuotaConfig:
    max_runs: int = 0          # 0 means disabled
    window_seconds: int = 3600
    state_dir: str = "/tmp/cronwrap/quota"

    def __post_init__(self) -> None:
        if self.max_runs < 0:
            raise ValueError("max_runs must be >= 0")
        if self.window_seconds <= 0:
            raise ValueError("window_seconds must be > 0")
        if not self.state_dir:
            raise ValueError("state_dir must not be empty")

    @classmethod
    def from_env(cls) -> "QuotaConfig":
        return cls(
            max_runs=int(os.environ.get("CRONWRAP_QUOTA_MAX_RUNS", "0")),
            window_seconds=int(os.environ.get("CRONWRAP_QUOTA_WINDOW", "3600")),
            state_dir=os.environ.get("CRONWRAP_QUOTA_STATE_DIR", "/tmp/cronwrap/quota"),
        )


@dataclass
class QuotaState:
    timestamps: List[float] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"timestamps": self.timestamps}

    @classmethod
    def from_dict(cls, data: dict) -> "QuotaState":
        return cls(timestamps=data.get("timestamps", []))

    def prune(self, window_seconds: int, now: float) -> None:
        cutoff = now - window_seconds
        self.timestamps = [t for t in self.timestamps if t >= cutoff]

    def count(self) -> int:
        return len(self.timestamps)

    def record(self, now: float) -> None:
        self.timestamps.append(now)


def _state_path(cfg: QuotaConfig, job_id: str) -> Path:
    return Path(cfg.state_dir) / f"{job_id}.quota.json"


def load_quota_state(cfg: QuotaConfig, job_id: str) -> QuotaState:
    path = _state_path(cfg, job_id)
    if not path.exists():
        return QuotaState()
    try:
        return QuotaState.from_dict(json.loads(path.read_text()))
    except Exception:
        return QuotaState()


def save_quota_state(cfg: QuotaConfig, job_id: str, state: QuotaState) -> None:
    path = _state_path(cfg, job_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state.to_dict()))


def check_quota(cfg: QuotaConfig, job_id: str, now: float | None = None) -> QuotaState:
    """Check and record a run. Raises QuotaExceededError if limit is hit."""
    if cfg.max_runs == 0:
        return QuotaState()
    if now is None:
        now = time.time()
    state = load_quota_state(cfg, job_id)
    state.prune(cfg.window_seconds, now)
    if state.count() >= cfg.max_runs:
        raise QuotaExceededError(
            f"Job '{job_id}' has reached {cfg.max_runs} runs "
            f"within {cfg.window_seconds}s window."
        )
    state.record(now)
    save_quota_state(cfg, job_id, state)
    return state


def quota_summary(cfg: QuotaConfig, job_id: str, now: float | None = None) -> str:
    if cfg.max_runs == 0:
        return "quota: disabled"
    if now is None:
        now = time.time()
    state = load_quota_state(cfg, job_id)
    state.prune(cfg.window_seconds, now)
    return (
        f"quota: {state.count()}/{cfg.max_runs} runs "
        f"in last {cfg.window_seconds}s window"
    )
