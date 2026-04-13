"""Unified configuration dataclass that aggregates all sub-configs."""
from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class CronwrapConfig:
    """Top-level configuration for a cronwrap invocation."""

    # Retry
    max_attempts: int = 1
    retry_delay: float = 0.0

    # Logging
    log_level: str = "INFO"
    log_file: str = ""

    # Alerts
    alert_on_failure: bool = False
    alert_email: str = ""

    # Schedule
    schedule: str = ""  # cron expression; empty means "always run"

    def __post_init__(self) -> None:
        self.log_level = self.log_level.upper()

        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")

        if self.retry_delay < 0:
            raise ValueError("retry_delay must be >= 0")

        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if self.log_level not in valid_levels:
            raise ValueError(
                f"log_level must be one of {sorted(valid_levels)}, got {self.log_level!r}"
            )

        # Validate schedule expression if provided
        if self.schedule:
            try:
                from cronwrap.scheduler import ScheduleConfig  # noqa: F401
                ScheduleConfig(expression=self.schedule)
            except ValueError as exc:
                raise ValueError(f"Invalid schedule expression: {exc}") from exc


def load_config_from_env() -> CronwrapConfig:
    """Build a CronwrapConfig from environment variables."""
    return CronwrapConfig(
        max_attempts=int(os.environ.get("CRONWRAP_MAX_ATTEMPTS", "1")),
        retry_delay=float(os.environ.get("CRONWRAP_RETRY_DELAY", "0.0")),
        log_level=os.environ.get("CRONWRAP_LOG_LEVEL", "INFO"),
        log_file=os.environ.get("CRONWRAP_LOG_FILE", ""),
        alert_on_failure=os.environ.get("CRONWRAP_ALERT_ON_FAILURE", "").lower()
        in {"1", "true", "yes"},
        alert_email=os.environ.get("CRONWRAP_ALERT_EMAIL", ""),
        schedule=os.environ.get("CRONWRAP_SCHEDULE", ""),
    )
