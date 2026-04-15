"""Runbook link attachment for cron job alerts and reports."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional
import os

_URL_RE = re.compile(r"^https?://.+", re.IGNORECASE)
_MAX_TITLE_LEN = 120
_MAX_URL_LEN = 2048


@dataclass
class RunbookConfig:
    """Configuration for an optional runbook URL attached to a job."""

    url: Optional[str] = None
    title: str = "Runbook"
    enabled: bool = True

    def __post_init__(self) -> None:
        self.title = self.title.strip()
        if len(self.title) > _MAX_TITLE_LEN:
            raise ValueError(
                f"title must be {_MAX_TITLE_LEN} characters or fewer, "
                f"got {len(self.title)}"
            )
        if self.url is not None:
            self.url = self.url.strip()
            if len(self.url) > _MAX_URL_LEN:
                raise ValueError(
                    f"url must be {_MAX_URL_LEN} characters or fewer"
                )
            if not _URL_RE.match(self.url):
                raise ValueError(
                    f"url must start with http:// or https://, got: {self.url!r}"
                )

    @classmethod
    def from_env(cls) -> "RunbookConfig":
        """Build a RunbookConfig from environment variables.

        CRONWRAP_RUNBOOK_URL   – URL to the runbook (optional)
        CRONWRAP_RUNBOOK_TITLE – display title (default: 'Runbook')
        CRONWRAP_RUNBOOK_ENABLED – '0' or 'false' to disable
        """
        raw_enabled = os.environ.get("CRONWRAP_RUNBOOK_ENABLED", "true")
        enabled = raw_enabled.strip().lower() not in ("0", "false", "no")
        url = os.environ.get("CRONWRAP_RUNBOOK_URL") or None
        title = os.environ.get("CRONWRAP_RUNBOOK_TITLE", "Runbook")
        return cls(url=url, title=title, enabled=enabled)


def runbook_summary(cfg: RunbookConfig) -> str:
    """Return a human-readable one-line summary of the runbook config."""
    if not cfg.enabled or cfg.url is None:
        return "runbook: not configured"
    return f"runbook: {cfg.title} -> {cfg.url}"


def format_runbook_line(cfg: RunbookConfig) -> Optional[str]:
    """Return a formatted string suitable for embedding in alerts/emails.

    Returns None when the runbook is disabled or has no URL.
    """
    if not cfg.enabled or cfg.url is None:
        return None
    return f"[{cfg.title}]({cfg.url})"
