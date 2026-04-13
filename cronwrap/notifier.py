"""Notification dispatch layer — routes alerts via email or stdout."""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Optional

from cronwrap.alerts import AlertConfig, build_alert_email, send_alert
from cronwrap.retry import RetryResult
from cronwrap.runner import RunResult


@dataclass
class NotifierConfig:
    """Controls how and when notifications are dispatched."""

    enabled: bool = True
    # If True, also print the alert body to stdout regardless of email config
    echo: bool = False
    # Only notify on failure; suppress success notifications
    failure_only: bool = True
    alert: AlertConfig = field(default_factory=AlertConfig)

    @classmethod
    def from_env(cls) -> "NotifierConfig":
        import os

        alert = AlertConfig.from_env()
        return cls(
            enabled=os.environ.get("CRONWRAP_NOTIFY_ENABLED", "true").lower() != "false",
            echo=os.environ.get("CRONWRAP_NOTIFY_ECHO", "false").lower() == "true",
            failure_only=os.environ.get("CRONWRAP_NOTIFY_FAILURE_ONLY", "true").lower() != "false",
            alert=alert,
        )


def notify(
    result: RunResult,
    retry_result: Optional[RetryResult],
    config: Optional[NotifierConfig] = None,
) -> bool:
    """Dispatch a notification for *result*.

    Returns True if a notification was sent, False otherwise.
    """
    if config is None:
        config = NotifierConfig()

    if not config.enabled:
        return False

    if config.failure_only and result.success:
        return False

    subject, body = build_alert_email(result, retry_result=retry_result)

    if config.echo:
        print(f"[cronwrap] {subject}", file=sys.stdout)
        print(body, file=sys.stdout)

    if config.alert.smtp_host and config.alert.to_address:
        send_alert(subject, body, config.alert)
        return True

    # No SMTP configured — echoing is the only output
    return config.echo
