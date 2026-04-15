"""Debounce support: suppress duplicate job alerts within a cooldown window."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path

_DEFAULT_WINDOW: int = 300  # seconds
_DEFAULT_STATE_DIR: str = "/tmp/cronwrap/debounce"


@dataclass
class DebounceConfig:
    window_seconds: int = _DEFAULT_WINDOW
    state_dir: str = _DEFAULT_STATE_DIR
    enabled: bool = True

    def __post_init__(self) -> None:
        if self.window_seconds <= 0:
            raise ValueError("window_seconds must be a positive integer")
        if not self.state_dir:
            raise ValueError("state_dir must not be empty")

    @classmethod
    def from_env(cls) -> "DebounceConfig":
        enabled = os.environ.get("CRONWRAP_DEBOUNCE_ENABLED", "true").lower() != "false"
        window = int(os.environ.get("CRONWRAP_DEBOUNCE_WINDOW", str(_DEFAULT_WINDOW)))
        state_dir = os.environ.get("CRONWRAP_DEBOUNCE_STATE_DIR", _DEFAULT_STATE_DIR)
        return cls(window_seconds=window, state_dir=state_dir, enabled=enabled)


@dataclass
class DebounceState:
    job_id: str
    last_alert_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {"job_id": self.job_id, "last_alert_at": self.last_alert_at}

    @classmethod
    def from_dict(cls, data: dict) -> "DebounceState":
        return cls(job_id=data["job_id"], last_alert_at=data["last_alert_at"])


def _state_path(state_dir: str, job_id: str) -> Path:
    safe = job_id.replace("/", "_").replace(" ", "_")
    return Path(state_dir) / f"{safe}.json"


def should_alert(config: DebounceConfig, job_id: str, now: float | None = None) -> bool:
    """Return True if enough time has passed since the last alert for job_id."""
    if not config.enabled:
        return True
    now = now if now is not None else time.time()
    path = _state_path(config.state_dir, job_id)
    if path.exists():
        try:
            data = json.loads(path.read_text())
            state = DebounceState.from_dict(data)
            if now - state.last_alert_at < config.window_seconds:
                return False
        except (json.JSONDecodeError, KeyError):
            pass
    return True


def record_alert(config: DebounceConfig, job_id: str, now: float | None = None) -> None:
    """Persist the current timestamp as the last alert time for job_id."""
    if not config.enabled:
        return
    now = now if now is not None else time.time()
    path = _state_path(config.state_dir, job_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    state = DebounceState(job_id=job_id, last_alert_at=now)
    path.write_text(json.dumps(state.to_dict()))


def debounce_summary(config: DebounceConfig, job_id: str, now: float | None = None) -> str:
    """Return a human-readable summary of the debounce state for job_id."""
    now = now if now is not None else time.time()
    path = _state_path(config.state_dir, job_id)
    if not config.enabled:
        return f"debounce disabled for '{job_id}'"
    if not path.exists():
        return f"no previous alert recorded for '{job_id}'"
    try:
        data = json.loads(path.read_text())
        state = DebounceState.from_dict(data)
        elapsed = now - state.last_alert_at
        remaining = max(0.0, config.window_seconds - elapsed)
        return (
            f"job '{job_id}': last alert {elapsed:.1f}s ago, "
            f"cooldown remaining {remaining:.1f}s"
        )
    except (json.JSONDecodeError, KeyError):
        return f"corrupt debounce state for '{job_id}'"
