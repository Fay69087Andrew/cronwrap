"""Structured event log for recording lifecycle events during a job run."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional


_VALID_LEVELS = {"debug", "info", "warning", "error"}


@dataclass
class EventLogConfig:
    enabled: bool = True
    max_events: int = 200
    level: str = "info"

    def __post_init__(self) -> None:
        self.level = self.level.lower()
        if self.level not in _VALID_LEVELS:
            raise ValueError(f"level must be one of {sorted(_VALID_LEVELS)}, got {self.level!r}")
        if self.max_events <= 0:
            raise ValueError("max_events must be a positive integer")

    @classmethod
    def from_env(cls) -> "EventLogConfig":
        enabled = os.environ.get("CRONWRAP_EVENTLOG_ENABLED", "true").lower() != "false"
        max_events = int(os.environ.get("CRONWRAP_EVENTLOG_MAX_EVENTS", "200"))
        level = os.environ.get("CRONWRAP_EVENTLOG_LEVEL", "info")
        return cls(enabled=enabled, max_events=max_events, level=level)


@dataclass
class Event:
    name: str
    level: str
    message: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "level": self.level,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
        }


@dataclass
class EventLog:
    config: EventLogConfig = field(default_factory=EventLogConfig)
    _events: List[Event] = field(default_factory=list, init=False, repr=False)

    def record(self, name: str, message: str, level: str = "info", data: Optional[dict] = None) -> None:
        if not self.config.enabled:
            return
        if len(self._events) >= self.config.max_events:
            return
        self._events.append(Event(name=name, level=level, message=message, data=data or {}))

    @property
    def events(self) -> List[Event]:
        return list(self._events)

    def by_level(self, level: str) -> List[Event]:
        return [e for e in self._events if e.level == level]

    def summary(self) -> dict:
        counts: dict = {}
        for e in self._events:
            counts[e.level] = counts.get(e.level, 0) + 1
        return {"total": len(self._events), "by_level": counts}
