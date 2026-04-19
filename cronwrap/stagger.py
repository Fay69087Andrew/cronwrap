"""Stagger: spread job starts across a time window to avoid thundering herd."""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field


@dataclass
class StaggerConfig:
    enabled: bool = False
    window_seconds: int = 60
    job_id: str = "default"

    def __post_init__(self) -> None:
        if not isinstance(self.enabled, bool):
            raise TypeError("enabled must be a bool")
        if self.window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        if not self.job_id or not self.job_id.strip():
            raise ValueError("job_id must not be empty")
        self.job_id = self.job_id.strip()

    @classmethod
    def from_env(cls) -> "StaggerConfig":
        enabled_raw = os.environ.get("CRONWRAP_STAGGER_ENABLED", "false").lower()
        enabled = enabled_raw in ("1", "true", "yes")
        window = int(os.environ.get("CRONWRAP_STAGGER_WINDOW", "60"))
        job_id = os.environ.get("CRONWRAP_STAGGER_JOB_ID", "default")
        return cls(enabled=enabled, window_seconds=window, job_id=job_id)


def compute_stagger_delay(cfg: StaggerConfig) -> float:
    """Deterministically compute a delay in [0, window_seconds) based on job_id."""
    if not cfg.enabled:
        return 0.0
    digest = hashlib.md5(cfg.job_id.encode()).hexdigest()
    fraction = int(digest[:8], 16) / 0xFFFFFFFF
    return fraction * cfg.window_seconds


def stagger_summary(cfg: StaggerConfig, delay: float) -> str:
    if not cfg.enabled:
        return "stagger disabled"
    return (
        f"stagger enabled | job_id={cfg.job_id} "
        f"window={cfg.window_seconds}s delay={delay:.2f}s"
    )
