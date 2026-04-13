"""cronwrap — A CLI wrapper around cron jobs with logging, alerts, and retry."""

__version__ = "0.2.0"

from cronwrap.runner import RunResult, run_command
from cronwrap.alerts import AlertConfig, send_alert

__all__ = [
    "RunResult",
    "run_command",
    "AlertConfig",
    "send_alert",
]
