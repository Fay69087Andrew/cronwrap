"""Cooldown: prevent a job from running again too soon after a previous run."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CooldownConfig:
    enabled: bool = False
    min_interval: float = 60.0  # seconds
    state_dir: str = "/tmp/cronwrap/cooldown"

    def __post_init__(self) -> None:
        if self.min_interval <= 0:
            raise ValueError("min_interval must be positive")
        if not self.state_dir:
            raise ValueError("state_dir must not be empty")

    @classmethod
    def from_env(cls) -> "CooldownConfig":
        enabled = os.environ.get("CRONWRAP_COOLDOWN_ENABLED", "false").lower() == "true"
        min_interval = float(os.environ.get("CRONWRAP_COOLDOWN_MIN_INTERVAL", "60"))
        state_dir = os.environ.get("CRONWRAP_COOLDOWN_STATE_DIR", "/tmp/cronwrap/cooldown")
        return cls(enabled=enabled, min_interval=min_interval, state_dir=state_dir)


@dataclass
class CooldownState:
    last_run: float = 0.0

    def to_dict(self) -> dict:
        return {"last_run": self.last_run}

    @classmethod
    def from_dict(cls, data: dict) -> "CooldownState":
        return cls(last_run=float(data.get("last_run", 0.0)))


def _state_path(cfg: CooldownConfig, job_id: str) -> Path:
    return Path(cfg.state_dir) / f"{job_id}.json"


def load_state(cfg: CooldownConfig, job_id: str) -> CooldownState:
    path = _state_path(cfg, job_id)
    if path.exists():
        with open(path) as f:
            return CooldownState.from_dict(json.load(f))
    return CooldownState()


def save_state(cfg: CooldownConfig, job_id: str, state: CooldownState) -> None:
    path = _state_path(cfg, job_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(state.to_dict(), f)


def is_cooling_down(cfg: CooldownConfig, job_id: str, now: float | None = None) -> bool:
    """Return True if the job is still within its cooldown window."""
    if not cfg.enabled:
        return False
    now = now if now is not None else time.time()
    state = load_state(cfg, job_id)
    return (now - state.last_run) < cfg.min_interval


def record_run(cfg: CooldownConfig, job_id: str, now: float | None = None) -> None:
    """Record that the job has just run."""
    now = now if now is not None else time.time()
    save_state(cfg, job_id, CooldownState(last_run=now))


def cooldown_summary(cfg: CooldownConfig, job_id: str, now: float | None = None) -> str:
    now = now if now is not None else time.time()
    state = load_state(cfg, job_id)
    elapsed = now - state.last_run
    remaining = max(0.0, cfg.min_interval - elapsed)
    return (
        f"cooldown job_id={job_id} enabled={cfg.enabled} "
        f"min_interval={cfg.min_interval}s elapsed={elapsed:.1f}s remaining={remaining:.1f}s"
    )
