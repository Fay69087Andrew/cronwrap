"""Step-level logging: record named steps within a job run with timing and status."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Step:
    name: str
    status: str  # 'ok' | 'fail' | 'skip'
    duration_s: float
    message: str = ""

    def succeeded(self) -> bool:
        return self.status == "ok"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "status": self.status,
            "duration_s": round(self.duration_s, 4),
            "message": self.message,
        }


@dataclass
class StepLog:
    job_name: str
    steps: List[Step] = field(default_factory=list)

    def record(self, name: str, status: str, duration_s: float, message: str = "") -> Step:
        if status not in ("ok", "fail", "skip"):
            raise ValueError(f"Invalid status {status!r}; must be 'ok', 'fail', or 'skip'")
        if not name or not name.strip():
            raise ValueError("Step name must not be empty")
        step = Step(name=name.strip(), status=status, duration_s=duration_s, message=message)
        self.steps.append(step)
        return step

    def failed_steps(self) -> List[Step]:
        return [s for s in self.steps if s.status == "fail"]

    def any_failed(self) -> bool:
        return any(s.status == "fail" for s in self.steps)

    def total_duration(self) -> float:
        return sum(s.duration_s for s in self.steps)

    def summary(self) -> str:
        total = len(self.steps)
        ok = sum(1 for s in self.steps if s.status == "ok")
        fail = sum(1 for s in self.steps if s.status == "fail")
        skip = sum(1 for s in self.steps if s.status == "skip")
        dur = round(self.total_duration(), 3)
        return (
            f"job={self.job_name} steps={total} ok={ok} fail={fail} "
            f"skip={skip} total_duration={dur}s"
        )

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "steps": [s.to_dict() for s in self.steps],
            "any_failed": self.any_failed(),
            "total_duration_s": round(self.total_duration(), 4),
        }
