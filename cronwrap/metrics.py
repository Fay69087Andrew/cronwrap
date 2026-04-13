"""Lightweight in-process metrics collection for cronwrap job runs."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class JobMetric:
    """Single timing/outcome record for one job execution."""

    command: str
    exit_code: int
    duration_seconds: float
    timestamp: float = field(default_factory=time.time)

    @property
    def succeeded(self) -> bool:
        return self.exit_code == 0

    def to_dict(self) -> dict:
        return {
            "command": self.command,
            "exit_code": self.exit_code,
            "duration_seconds": round(self.duration_seconds, 4),
            "timestamp": self.timestamp,
            "succeeded": self.succeeded,
        }


@dataclass
class MetricsStore:
    """Accumulates JobMetric records during a process lifetime."""

    _records: List[JobMetric] = field(default_factory=list, init=False, repr=False)

    def record(self, metric: JobMetric) -> None:
        """Append a new metric record."""
        self._records.append(metric)

    def all(self) -> List[JobMetric]:
        return list(self._records)

    def for_command(self, command: str) -> List[JobMetric]:
        return [r for r in self._records if r.command == command]

    def summary(self) -> Dict[str, object]:
        """Return aggregate stats across all recorded metrics."""
        if not self._records:
            return {"total": 0, "succeeded": 0, "failed": 0, "avg_duration": None}
        succeeded = sum(1 for r in self._records if r.succeeded)
        avg = sum(r.duration_seconds for r in self._records) / len(self._records)
        return {
            "total": len(self._records),
            "succeeded": succeeded,
            "failed": len(self._records) - succeeded,
            "avg_duration": round(avg, 4),
        }

    def clear(self) -> None:
        self._records.clear()


# Module-level default store
_default_store: Optional[MetricsStore] = None


def get_store() -> MetricsStore:
    """Return (lazily created) module-level MetricsStore."""
    global _default_store
    if _default_store is None:
        _default_store = MetricsStore()
    return _default_store
