"""Surge detection: flag when a job's runtime significantly exceeds its historical average."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class SurgeConfig:
    enabled: bool = True
    # Multiplier above the rolling average that triggers a surge flag
    threshold_multiplier: float = 2.0
    # Number of recent runs to include in the rolling average
    window: int = 10
    state_dir: str = "/tmp/cronwrap/surge"

    def __post_init__(self) -> None:
        if self.threshold_multiplier <= 1.0:
            raise ValueError("threshold_multiplier must be greater than 1.0")
        if self.window < 1:
            raise ValueError("window must be at least 1")
        if not self.state_dir:
            raise ValueError("state_dir must not be empty")

    @classmethod
    def from_env(cls) -> "SurgeConfig":
        enabled = os.environ.get("CRONWRAP_SURGE_ENABLED", "true").lower() != "false"
        multiplier = float(os.environ.get("CRONWRAP_SURGE_THRESHOLD_MULTIPLIER", "2.0"))
        window = int(os.environ.get("CRONWRAP_SURGE_WINDOW", "10"))
        state_dir = os.environ.get("CRONWRAP_SURGE_STATE_DIR", "/tmp/cronwrap/surge")
        return cls(enabled=enabled, threshold_multiplier=multiplier, window=window, state_dir=state_dir)


@dataclass
class SurgeState:
    durations: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"durations": self.durations}

    @classmethod
    def from_dict(cls, data: dict) -> "SurgeState":
        return cls(durations=list(data.get("durations", [])))

    def rolling_average(self, window: int) -> Optional[float]:
        recent = self.durations[-window:]
        if not recent:
            return None
        return sum(recent) / len(recent)

    def record(self, duration: float, window: int) -> None:
        self.durations.append(duration)
        # Keep only enough history
        if len(self.durations) > window * 2:
            self.durations = self.durations[-(window * 2):]


def _state_path(cfg: SurgeConfig, job_id: str) -> Path:
    return Path(cfg.state_dir) / f"{job_id}.json"


def load_surge_state(cfg: SurgeConfig, job_id: str) -> SurgeState:
    path = _state_path(cfg, job_id)
    if not path.exists():
        return SurgeState()
    try:
        data = json.loads(path.read_text())
        return SurgeState.from_dict(data)
    except (json.JSONDecodeError, KeyError):
        return SurgeState()


def save_surge_state(cfg: SurgeConfig, job_id: str, state: SurgeState) -> None:
    path = _state_path(cfg, job_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state.to_dict()))


def check_surge(cfg: SurgeConfig, job_id: str, duration: float) -> tuple[bool, Optional[float]]:
    """Record duration and return (is_surge, rolling_average)."""
    if not cfg.enabled:
        return False, None
    state = load_surge_state(cfg, job_id)
    avg = state.rolling_average(cfg.window)
    state.record(duration, cfg.window)
    save_surge_state(cfg, job_id, state)
    if avg is None:
        return False, None
    is_surge = duration > avg * cfg.threshold_multiplier
    return is_surge, avg


def surge_summary(is_surge: bool, duration: float, avg: Optional[float]) -> str:
    if avg is None:
        return f"surge=no (no baseline) duration={duration:.2f}s"
    if is_surge:
        return f"surge=YES duration={duration:.2f}s avg={avg:.2f}s"
    return f"surge=no duration={duration:.2f}s avg={avg:.2f}s"
