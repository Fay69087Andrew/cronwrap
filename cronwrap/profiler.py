"""Execution time profiling for cron jobs."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ProfilerConfig:
    """Configuration for job execution profiling."""
    enabled: bool = True
    warn_threshold_seconds: float = 60.0
    critical_threshold_seconds: float = 300.0

    def __post_init__(self) -> None:
        if self.warn_threshold_seconds <= 0:
            raise ValueError("warn_threshold_seconds must be positive")
        if self.critical_threshold_seconds <= 0:
            raise ValueError("critical_threshold_seconds must be positive")
        if self.critical_threshold_seconds < self.warn_threshold_seconds:
            raise ValueError(
                "critical_threshold_seconds must be >= warn_threshold_seconds"
            )

    @classmethod
    def from_env(cls, env: dict) -> "ProfilerConfig":
        enabled = env.get("CRONWRAP_PROFILER_ENABLED", "true").lower() != "false"
        warn = float(env.get("CRONWRAP_PROFILER_WARN_SECONDS", "60"))
        critical = float(env.get("CRONWRAP_PROFILER_CRITICAL_SECONDS", "300"))
        return cls(enabled=enabled, warn_threshold_seconds=warn, critical_threshold_seconds=critical)


@dataclass
class ProfileResult:
    """Result of profiling a job execution."""
    elapsed_seconds: float
    warn_threshold_seconds: float
    critical_threshold_seconds: float
    label: str = ""

    @property
    def level(self) -> str:
        """Return severity level based on elapsed time."""
        if self.elapsed_seconds >= self.critical_threshold_seconds:
            return "critical"
        if self.elapsed_seconds >= self.warn_threshold_seconds:
            return "warn"
        return "ok"

    def summary(self) -> str:
        prefix = f"[{self.label}] " if self.label else ""
        return (
            f"{prefix}elapsed={self.elapsed_seconds:.3f}s "
            f"level={self.level} "
            f"(warn>={self.warn_threshold_seconds}s "
            f"critical>={self.critical_threshold_seconds}s)"
        )


class Profiler:
    """Context manager that measures elapsed wall-clock time."""

    def __init__(self, config: ProfilerConfig, label: str = "") -> None:
        self.config = config
        self.label = label
        self._start: Optional[float] = None
        self.result: Optional[ProfileResult] = None

    def __enter__(self) -> "Profiler":
        self._start = time.monotonic()
        return self

    def __exit__(self, *_) -> None:
        elapsed = time.monotonic() - (self._start or 0.0)
        self.result = ProfileResult(
            elapsed_seconds=elapsed,
            warn_threshold_seconds=self.config.warn_threshold_seconds,
            critical_threshold_seconds=self.config.critical_threshold_seconds,
            label=self.label,
        )
