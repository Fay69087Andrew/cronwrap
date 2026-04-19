"""drain.py – graceful-shutdown drain window for in-flight cron jobs.

When a termination signal is received the drain window gives the job a
configured number of seconds to finish before a hard kill is issued.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DrainConfig:
    enabled: bool = True
    window_seconds: float = 30.0
    poll_interval: float = 0.5

    def __post_init__(self) -> None:
        if not isinstance(self.enabled, bool):
            raise TypeError("enabled must be a bool")
        if self.window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        if self.poll_interval <= 0:
            raise ValueError("poll_interval must be positive")
        if self.poll_interval > self.window_seconds:
            raise ValueError("poll_interval must not exceed window_seconds")

    @classmethod
    def from_env(cls) -> "DrainConfig":
        enabled = os.environ.get("CRONWRAP_DRAIN_ENABLED", "true").lower() == "true"
        window = float(os.environ.get("CRONWRAP_DRAIN_WINDOW_SECONDS", "30"))
        poll = float(os.environ.get("CRONWRAP_DRAIN_POLL_INTERVAL", "0.5"))
        return cls(enabled=enabled, window_seconds=window, poll_interval=poll)


@dataclass
class DrainResult:
    drained: bool
    elapsed_seconds: float
    timed_out: bool

    def __str__(self) -> str:
        status = "timed_out" if self.timed_out else ("drained" if self.drained else "skipped")
        return f"DrainResult(status={status}, elapsed={self.elapsed_seconds:.2f}s)"


def wait_for_drain(
    cfg: DrainConfig,
    is_done_fn,  # callable[[], bool]
    *,
    _sleep=time.sleep,
    _time=time.monotonic,
) -> DrainResult:
    """Poll *is_done_fn* until it returns True or the drain window expires."""
    if not cfg.enabled:
        return DrainResult(drained=False, elapsed_seconds=0.0, timed_out=False)

    deadline = _time() + cfg.window_seconds
    while True:
        if is_done_fn():
            elapsed = _time() - (deadline - cfg.window_seconds)
            return DrainResult(drained=True, elapsed_seconds=elapsed, timed_out=False)
        if _time() >= deadline:
            return DrainResult(drained=False, elapsed_seconds=cfg.window_seconds, timed_out=True)
        _sleep(cfg.poll_interval)


def drain_summary(result: DrainResult) -> str:
    return str(result)
