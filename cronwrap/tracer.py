"""Execution tracer: records timestamped span events for a job run."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class TracerConfig:
    enabled: bool = True
    max_spans: int = 256

    def __post_init__(self) -> None:
        if self.max_spans < 1:
            raise ValueError("max_spans must be >= 1")

    @classmethod
    def from_env(cls, env: dict) -> "TracerConfig":
        enabled = env.get("CRONWRAP_TRACER_ENABLED", "true").lower() != "false"
        max_spans = int(env.get("CRONWRAP_TRACER_MAX_SPANS", "256"))
        return cls(enabled=enabled, max_spans=max_spans)


@dataclass
class Span:
    name: str
    start_time: float
    end_time: Optional[float] = None
    metadata: dict = field(default_factory=dict)

    @property
    def duration(self) -> Optional[float]:
        if self.end_time is None:
            return None
        return round(self.end_time - self.start_time, 6)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "metadata": self.metadata,
        }


class Tracer:
    def __init__(self, config: TracerConfig) -> None:
        self._config = config
        self._spans: List[Span] = []

    def start_span(self, name: str, metadata: Optional[dict] = None) -> Span:
        if not self._config.enabled:
            return Span(name=name, start_time=time.time())
        if len(self._spans) >= self._config.max_spans:
            self._spans.pop(0)
        span = Span(name=name, start_time=time.time(), metadata=metadata or {})
        self._spans.append(span)
        return span

    def end_span(self, span: Span) -> None:
        span.end_time = time.time()

    def spans(self) -> List[Span]:
        return list(self._spans)

    def summary(self) -> dict:
        spans = self.spans()
        durations = [s.duration for s in spans if s.duration is not None]
        return {
            "total_spans": len(spans),
            "total_duration": round(sum(durations), 6) if durations else 0.0,
            "spans": [s.to_dict() for s in spans],
        }
