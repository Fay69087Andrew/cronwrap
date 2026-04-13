"""Rate limiting for cron job alerts to prevent notification storms."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path

_DEFAULT_WINDOW_SECONDS = 3600  # 1 hour
_DEFAULT_MAX_ALERTS = 5
_DEFAULT_STATE_DIR = "/tmp/cronwrap/ratelimit"


@dataclass
class RateLimitConfig:
    window_seconds: int = _DEFAULT_WINDOW_SECONDS
    max_alerts: int = _DEFAULT_MAX_ALERTS
    state_dir: str = _DEFAULT_STATE_DIR

    def __post_init__(self) -> None:
        if self.window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        if self.max_alerts <= 0:
            raise ValueError("max_alerts must be positive")

    @classmethod
    def from_env(cls) -> "RateLimitConfig":
        return cls(
            window_seconds=int(
                os.environ.get("CRONWRAP_RATELIMIT_WINDOW", _DEFAULT_WINDOW_SECONDS)
            ),
            max_alerts=int(
                os.environ.get("CRONWRAP_RATELIMIT_MAX_ALERTS", _DEFAULT_MAX_ALERTS)
            ),
            state_dir=os.environ.get("CRONWRAP_RATELIMIT_STATE_DIR", _DEFAULT_STATE_DIR),
        )


@dataclass
class RateLimitState:
    timestamps: list[float] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"timestamps": self.timestamps}

    @classmethod
    def from_dict(cls, data: dict) -> "RateLimitState":
        return cls(timestamps=data.get("timestamps", []))


def _state_path(state_dir: str, job_name: str) -> Path:
    safe_name = job_name.replace("/", "_").replace(" ", "_")
    return Path(state_dir) / f"{safe_name}.json"


def _load_state(path: Path) -> RateLimitState:
    if not path.exists():
        return RateLimitState()
    try:
        return RateLimitState.from_dict(json.loads(path.read_text()))
    except (json.JSONDecodeError, OSError):
        return RateLimitState()


def _save_state(path: Path, state: RateLimitState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state.to_dict()))


def is_allowed(job_name: str, config: RateLimitConfig, now: float | None = None) -> bool:
    """Return True if an alert is allowed under the rate limit, and record it."""
    if now is None:
        now = time.time()
    path = _state_path(config.state_dir, job_name)
    state = _load_state(path)
    cutoff = now - config.window_seconds
    state.timestamps = [t for t in state.timestamps if t >= cutoff]
    if len(state.timestamps) >= config.max_alerts:
        return False
    state.timestamps.append(now)
    _save_state(path, state)
    return True


def remaining_alerts(job_name: str, config: RateLimitConfig, now: float | None = None) -> int:
    """Return how many more alerts are allowed in the current window."""
    if now is None:
        now = time.time()
    path = _state_path(config.state_dir, job_name)
    state = _load_state(path)
    cutoff = now - config.window_seconds
    recent = [t for t in state.timestamps if t >= cutoff]
    return max(0, config.max_alerts - len(recent))
