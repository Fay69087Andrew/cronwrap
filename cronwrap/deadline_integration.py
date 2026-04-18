"""Integration helpers for deadline enforcement."""
from __future__ import annotations

import sys
from typing import Optional

from cronwrap.deadline import DeadlineConfig, DeadlineExceededError, check_deadline, deadline_summary


def build_deadline_config() -> DeadlineConfig:
    """Build a DeadlineConfig from environment variables."""
    return DeadlineConfig.from_env()


def check_deadline_or_abort(config: Optional[DeadlineConfig] = None) -> None:
    """Check the deadline and abort (sys.exit) if it has passed.

    Prints a message to stderr before exiting.
    """
    if config is None:
        config = build_deadline_config()
    try:
        check_deadline(config)
    except DeadlineExceededError as exc:
        print(f"[cronwrap] deadline exceeded: {exc}", file=sys.stderr)
        sys.exit(1)


def deadline_report(config: DeadlineConfig) -> dict:
    """Return a dict suitable for inclusion in job metadata."""
    return {
        "deadline_enabled": config.enabled,
        "deadline": config.deadline.isoformat() if config.deadline else None,
        "summary": deadline_summary(config),
    }
