"""HTTP health-check ping support for cronwrap.

After a job completes (or fails) cronwrap can ping a URL so that an
external uptime-monitoring service (e.g. Healthchecks.io, Better Uptime)
knows the job ran.
"""
from __future__ import annotations

import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Optional

from cronwrap.runner import RunResult


@dataclass
class HealthcheckConfig:
    """Configuration for health-check pings."""

    ping_url: Optional[str] = None
    """Base URL to ping on success (e.g. https://hc-ping.com/<uuid>)."""

    ping_url_failure: Optional[str] = None
    """URL to ping on failure.  Defaults to ``ping_url + '/fail'``."""

    timeout_seconds: int = 10
    """HTTP request timeout in seconds."""

    enabled: bool = True

    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be a positive integer")

    @classmethod
    def from_env(cls) -> "HealthcheckConfig":
        """Build a :class:`HealthcheckConfig` from environment variables.

        Environment variables
        ---------------------
        CRONWRAP_HC_URL          Base ping URL (success).
        CRONWRAP_HC_FAIL_URL     Explicit failure URL (optional).
        CRONWRAP_HC_TIMEOUT      Request timeout in seconds (default 10).
        CRONWRAP_HC_ENABLED      Set to '0' or 'false' to disable.
        """
        enabled_raw = os.environ.get("CRONWRAP_HC_ENABLED", "1").lower()
        enabled = enabled_raw not in ("0", "false", "no")
        timeout = int(os.environ.get("CRONWRAP_HC_TIMEOUT", "10"))
        return cls(
            ping_url=os.environ.get("CRONWRAP_HC_URL") or None,
            ping_url_failure=os.environ.get("CRONWRAP_HC_FAIL_URL") or None,
            timeout_seconds=timeout,
            enabled=enabled,
        )


def _ping(url: str, timeout: int) -> bool:
    """Send a GET request to *url*.  Returns True on HTTP 2xx/3xx."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310
            return resp.status < 400
    except (urllib.error.URLError, OSError):
        return False


def send_healthcheck(result: RunResult, cfg: HealthcheckConfig) -> bool:
    """Ping the configured health-check URL based on *result*.

    Returns True if a ping was sent successfully, False otherwise.
    Does nothing (returns False) when disabled or no URL is configured.
    """
    if not cfg.enabled or not cfg.ping_url:
        return False

    if result.success:
        return _ping(cfg.ping_url, cfg.timeout_seconds)

    fail_url = cfg.ping_url_failure or cfg.ping_url.rstrip("/") + "/fail"
    return _ping(fail_url, cfg.timeout_seconds)
