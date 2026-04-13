"""Scheduler module: parse and evaluate cron expressions to determine
whether a job is due to run, and compute the next scheduled time."""
from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Optional

try:
    from croniter import croniter  # type: ignore
except ImportError:  # pragma: no cover
    croniter = None  # type: ignore


@dataclass
class ScheduleConfig:
    """Configuration for a cron schedule expression."""

    expression: str = "* * * * *"
    timezone: str = "UTC"

    def __post_init__(self) -> None:
        if croniter is None:
            raise RuntimeError(
                "croniter is required for schedule support: pip install croniter"
            )
        if not croniter.is_valid(self.expression):
            raise ValueError(f"Invalid cron expression: {self.expression!r}")


def is_due(config: ScheduleConfig, now: Optional[datetime.datetime] = None) -> bool:
    """Return True if the cron expression matches the current minute."""
    if now is None:
        now = datetime.datetime.utcnow()
    # Truncate to the current minute boundary
    minute_start = now.replace(second=0, microsecond=0)
    # croniter checks whether 'minute_start' is a scheduled time by
    # asking for the previous occurrence from one second later.
    base = minute_start - datetime.timedelta(seconds=1)
    itr = croniter(config.expression, base)
    next_time = itr.get_next(datetime.datetime)
    return next_time == minute_start


def next_run(config: ScheduleConfig, after: Optional[datetime.datetime] = None) -> datetime.datetime:
    """Return the next scheduled datetime after *after* (default: now)."""
    if after is None:
        after = datetime.datetime.utcnow()
    itr = croniter(config.expression, after)
    return itr.get_next(datetime.datetime)


def prev_run(config: ScheduleConfig, before: Optional[datetime.datetime] = None) -> datetime.datetime:
    """Return the most recent scheduled datetime before *before* (default: now)."""
    if before is None:
        before = datetime.datetime.utcnow()
    itr = croniter(config.expression, before)
    return itr.get_prev(datetime.datetime)
