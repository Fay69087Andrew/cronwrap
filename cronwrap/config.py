"""Unified configuration loader for cronwrap from environment and defaults."""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CronwrapConfig:
    """Aggregated runtime configuration for a cronwrap invocation."""

    job_name: str = "cronwrap-job"
    max_attempts: int = 1
    retry_delay: float = 0.0
    log_file: Optional[str] = None
    log_level: str = "INFO"
    alert_on_failure: bool = False
    smtp_host: str = "localhost"
    smtp_port: int = 25
    alert_from: str = "cronwrap@localhost"
    alert_to: str = ""

    def __post_init__(self):
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.retry_delay < 0:
            raise ValueError("retry_delay must be >= 0")
        self.log_level = self.log_level.upper()


def load_config_from_env() -> CronwrapConfig:
    """Build a CronwrapConfig from environment variables with sensible defaults."""
    return CronwrapConfig(
        job_name=os.environ.get("CRONWRAP_JOB_NAME", "cronwrap-job"),
        max_attempts=int(os.environ.get("CRONWRAP_MAX_ATTEMPTS", "1")),
        retry_delay=float(os.environ.get("CRONWRAP_RETRY_DELAY", "0.0")),
        log_file=os.environ.get("CRONWRAP_LOG_FILE") or None,
        log_level=os.environ.get("CRONWRAP_LOG_LEVEL", "INFO"),
        alert_on_failure=os.environ.get("CRONWRAP_ALERT_ON_FAILURE", "").lower() in ("1", "true", "yes"),
        smtp_host=os.environ.get("CRONWRAP_SMTP_HOST", "localhost"),
        smtp_port=int(os.environ.get("CRONWRAP_SMTP_PORT", "25")),
        alert_from=os.environ.get("CRONWRAP_ALERT_FROM", "cronwrap@localhost"),
        alert_to=os.environ.get("CRONWRAP_ALERT_TO", ""),
    )
