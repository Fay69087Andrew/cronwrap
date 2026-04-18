"""Watchdog: detect and report stale/missing job runs."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class WatchdogConfig:
    enabled: bool = True
    max_silence_seconds: int = 3600
    state_dir: str = "/tmp/cronwrap/watchdog"
    job_name: str = "default"

    def __post_init__(self) -> None:
        if not isinstance(self.enabled, bool):
            raise TypeError("enabled must be a bool")
        if self.max_silence_seconds <= 0:
            raise ValueError("max_silence_seconds must be positive")
        if not self.state_dir.strip():
            raise ValueError("state_dir must not be empty")
        if not self.job_name.strip():
            raise ValueError("job_name must not be empty")

    @classmethod
    def from_env(cls) -> "WatchdogConfig":
        return cls(
            enabled=os.environ.get("CRONWRAP_WATCHDOG_ENABLED", "true").lower() == "true",
            max_silence_seconds=int(os.environ.get("CRONWRAP_WATCHDOG_MAX_SILENCE", "3600")),
            state_dir=os.environ.get("CRONWRAP_WATCHDOG_STATE_DIR", "/tmp/cronwrap/watchdog"),
            job_name=os.environ.get("CRONWRAP_JOB_NAME", "default"),
        )


@dataclass
class WatchdogState:
    job_name: str
    last_seen: Optional[datetime] = None
    stale: bool = False

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "stale": self.stale,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "WatchdogState":
        last_seen = None
        if d.get("last_seen"):
            last_seen = datetime.fromisoformat(d["last_seen"])
        return cls(job_name=d["job_name"], last_seen=last_seen, stale=d.get("stale", False))


def check_stale(state: WatchdogState, cfg: WatchdogConfig, now: Optional[datetime] = None) -> bool:
    """Return True if the job is considered stale."""
    if not cfg.enabled:
        return False
    if state.last_seen is None:
        return True
    now = now or datetime.now(timezone.utc)
    elapsed = (now - state.last_seen).total_seconds()
    return elapsed > cfg.max_silence_seconds


def watchdog_summary(state: WatchdogState, cfg: WatchdogConfig) -> str:
    if not cfg.enabled:
        return "watchdog disabled"
    if state.last_seen is None:
        return f"watchdog[{state.job_name}]: never seen"
    status = "STALE" if state.stale else "ok"
    return f"watchdog[{state.job_name}]: last_seen={state.last_seen.isoformat()} status={status}"
