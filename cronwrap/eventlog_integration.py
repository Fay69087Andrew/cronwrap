"""Integration helpers for EventLog within a cronwrap job run."""
from __future__ import annotations

import os
from typing import Optional

from cronwrap.eventlog import EventLog, EventLogConfig
from cronwrap.runner import RunResult


def build_event_log() -> EventLog:
    """Build an EventLog from environment variables."""
    return EventLog(config=EventLogConfig.from_env())


def record_run_events(log: EventLog, result: RunResult) -> None:
    """Record standard lifecycle events derived from a RunResult."""
    log.record(
        name="job.start",
        message=f"Job started: {result.command}",
        level="info",
        data={"command": result.command},
    )
    level = "info" if result.success else "error"
    log.record(
        name="job.finish",
        message=f"Job finished with exit code {result.exit_code}",
        level=level,
        data={"exit_code": result.exit_code, "success": result.success},
    )
    if result.duration_seconds is not None:
        log.record(
            name="job.duration",
            message=f"Job ran for {result.duration_seconds:.3f}s",
            level="info",
            data={"duration_seconds": result.duration_seconds},
        )


def eventlog_summary(log: EventLog) -> str:
    """Return a human-readable summary of recorded events."""
    s = log.summary()
    parts = [f"events={s['total']}"]
    for lvl, count in sorted(s["by_level"].items()):
        parts.append(f"{lvl}={count}")
    return "EventLog(" + ", ".join(parts) + ")"
