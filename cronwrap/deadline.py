"""Deadline enforcement: abort a job if a wall-clock deadline has passed."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


class DeadlineExceededError(Exception):
    """Raised when the current time is past the configured deadline."""


@dataclass
class DeadlineConfig:
    """Configuration for deadline enforcement."""

    deadline: Optional[datetime] = None  # UTC datetime; None means disabled
    enabled: bool = True

    def __post_init__(self) -> None:
        if self.deadline is not None:
            if not isinstance(self.deadline, datetime):
                raise TypeError("deadline must be a datetime object or None")
            if self.deadline.tzinfo is None:
                raise ValueError("deadline must be timezone-aware")

    @classmethod
    def from_env(cls) -> "DeadlineConfig":
        """Build config from environment variables.

        CRONWRAP_DEADLINE  – ISO-8601 UTC datetime string, e.g. 2025-12-31T23:59:00+00:00
        CRONWRAP_DEADLINE_ENABLED – 'false' to disable (default true)
        """
        enabled = os.environ.get("CRONWRAP_DEADLINE_ENABLED", "true").lower() != "false"
        raw = os.environ.get("CRONWRAP_DEADLINE", "").strip()
        deadline: Optional[datetime] = None
        if raw:
            deadline = datetime.fromisoformat(raw)
            if deadline.tzinfo is None:
                raise ValueError("CRONWRAP_DEADLINE must include timezone info")
        return cls(deadline=deadline, enabled=enabled)


def check_deadline(config: DeadlineConfig) -> None:
    """Raise DeadlineExceededError if the deadline has passed."""
    if not config.enabled or config.deadline is None:
        return
    now = datetime.now(tz=timezone.utc)
    if now >= config.deadline:
        raise DeadlineExceededError(
            f"Deadline {config.deadline.isoformat()} has passed (now={now.isoformat()})"
        )


def deadline_summary(config: DeadlineConfig) -> str:
    """Return a human-readable summary of the deadline configuration."""
    if not config.enabled or config.deadline is None:
        return "deadline: disabled"
    return f"deadline: {config.deadline.isoformat()}"
