"""Fence: prevent a job from running outside an allowed time window."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import time, datetime, timezone
from typing import Optional


class FenceViolationError(Exception):
    """Raised when a job runs outside its allowed window."""


@dataclass
class FenceConfig:
    enabled: bool = False
    window_start: time = field(default_factory=lambda: time(0, 0))
    window_end: time = field(default_factory=lambda: time(23, 59))
    timezone_name: str = "UTC"

    def __post_init__(self) -> None:
        if not isinstance(self.window_start, time):
            raise TypeError("window_start must be a datetime.time")
        if not isinstance(self.window_end, time):
            raise TypeError("window_end must be a datetime.time")
        if self.window_start >= self.window_end:
            raise ValueError("window_start must be before window_end")
        if not self.timezone_name or not self.timezone_name.strip():
            raise ValueError("timezone_name must not be empty")

    @classmethod
    def from_env(cls) -> "FenceConfig":
        enabled = os.environ.get("CRONWRAP_FENCE_ENABLED", "false").lower() == "true"
        start_str = os.environ.get("CRONWRAP_FENCE_START", "00:00")
        end_str = os.environ.get("CRONWRAP_FENCE_END", "23:59")
        tz = os.environ.get("CRONWRAP_FENCE_TIMEZONE", "UTC")
        window_start = time.fromisoformat(start_str)
        window_end = time.fromisoformat(end_str)
        return cls(enabled=enabled, window_start=window_start, window_end=window_end, timezone_name=tz)


def is_within_fence(cfg: FenceConfig, now: Optional[datetime] = None) -> bool:
    """Return True if *now* falls within the allowed window."""
    if not cfg.enabled:
        return True
    if now is None:
        now = datetime.now(timezone.utc)
    current_time = now.time().replace(tzinfo=None)
    return cfg.window_start <= current_time <= cfg.window_end


def check_fence_or_abort(cfg: FenceConfig, now: Optional[datetime] = None) -> None:
    """Raise SystemExit(1) when the job is outside its allowed window."""
    if not is_within_fence(cfg, now):
        raise SystemExit(1)


def fence_summary(cfg: FenceConfig, now: Optional[datetime] = None) -> str:
    within = is_within_fence(cfg, now)
    status = "allowed" if within else "blocked"
    return (
        f"fence enabled={cfg.enabled} window={cfg.window_start.isoformat()}-"
        f"{cfg.window_end.isoformat()} tz={cfg.timezone_name} status={status}"
    )
