"""Spillover detection: warn when a job runs longer than its scheduled interval."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Optional


@dataclass
class SpilloverConfig:
    """Configuration for spillover detection."""

    interval_seconds: float = 3600.0
    enabled: bool = True
    warn_only: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.enabled, bool):
            raise TypeError("enabled must be a bool")
        if not isinstance(self.warn_only, bool):
            raise TypeError("warn_only must be a bool")
        if self.interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")

    @classmethod
    def from_env(cls) -> "SpilloverConfig":
        enabled = os.environ.get("CRONWRAP_SPILLOVER_ENABLED", "true").lower() == "true"
        warn_only = os.environ.get("CRONWRAP_SPILLOVER_WARN_ONLY", "true").lower() == "true"
        interval = float(os.environ.get("CRONWRAP_SPILLOVER_INTERVAL", "3600"))
        return cls(interval_seconds=interval, enabled=enabled, warn_only=warn_only)


@dataclass
class SpilloverResult:
    """Result of a spillover check."""

    elapsed_seconds: float
    interval_seconds: float
    spilled: bool
    overflow_seconds: float = field(init=False)

    def __post_init__(self) -> None:
        self.overflow_seconds = max(0.0, self.elapsed_seconds - self.interval_seconds)

    def __str__(self) -> str:
        if not self.spilled:
            return (
                f"OK: elapsed {self.elapsed_seconds:.1f}s "
                f"within interval {self.interval_seconds:.1f}s"
            )
        return (
            f"SPILLOVER: elapsed {self.elapsed_seconds:.1f}s exceeded "
            f"interval {self.interval_seconds:.1f}s "
            f"by {self.overflow_seconds:.1f}s"
        )


def check_spillover(
    elapsed_seconds: float,
    cfg: Optional[SpilloverConfig] = None,
) -> SpilloverResult:
    """Return a SpilloverResult for the given elapsed time."""
    if cfg is None:
        cfg = SpilloverConfig()
    spilled = cfg.enabled and elapsed_seconds > cfg.interval_seconds
    return SpilloverResult(
        elapsed_seconds=elapsed_seconds,
        interval_seconds=cfg.interval_seconds,
        spilled=spilled,
    )


def spillover_summary(result: SpilloverResult) -> dict:
    """Return a plain-dict summary suitable for logging."""
    return {
        "spilled": result.spilled,
        "elapsed_seconds": result.elapsed_seconds,
        "interval_seconds": result.interval_seconds,
        "overflow_seconds": result.overflow_seconds,
    }
