"""Webhook notification support for cronwrap.

Sends an HTTP POST request to a configured URL when a job finishes,
optionally only on failure.
"""
from __future__ import annotations

import json
import os
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Optional

from cronwrap.runner import RunResult


@dataclass
class WebhookConfig:
    """Configuration for webhook notifications."""

    url: Optional[str] = None
    on_failure_only: bool = True
    timeout_seconds: int = 10
    extra_headers: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be a positive integer")

    @classmethod
    def from_env(cls) -> "WebhookConfig":
        """Build a WebhookConfig from environment variables.

        CRONWRAP_WEBHOOK_URL        – destination URL (empty → disabled)
        CRONWRAP_WEBHOOK_ON_FAILURE – '1' to notify only on failure (default)
        CRONWRAP_WEBHOOK_TIMEOUT    – request timeout in seconds (default 10)
        """
        url = os.environ.get("CRONWRAP_WEBHOOK_URL") or None
        on_failure_only = os.environ.get("CRONWRAP_WEBHOOK_ON_FAILURE", "1") == "1"
        timeout_seconds = int(os.environ.get("CRONWRAP_WEBHOOK_TIMEOUT", "10"))
        return cls(
            url=url,
            on_failure_only=on_failure_only,
            timeout_seconds=timeout_seconds,
        )


def _build_payload(result: RunResult) -> bytes:
    """Serialise a RunResult into a JSON payload."""
    data = {
        "command": result.command,
        "exit_code": result.exit_code,
        "success": result.success,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "duration_seconds": result.duration_seconds,
    }
    return json.dumps(data).encode("utf-8")


def send_webhook(result: RunResult, cfg: WebhookConfig) -> bool:
    """Send a webhook POST for *result* according to *cfg*.

    Returns True if the request was sent and received a 2xx response,
    False if it was skipped or failed.
    """
    if not cfg.url:
        return False
    if cfg.on_failure_only and result.success:
        return False

    payload = _build_payload(result)
    headers = {"Content-Type": "application/json", **cfg.extra_headers}
    req = urllib.request.Request(cfg.url, data=payload, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=cfg.timeout_seconds) as resp:
            return 200 <= resp.status < 300
    except urllib.error.URLError:
        return False
