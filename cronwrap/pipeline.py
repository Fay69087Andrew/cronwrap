"""Pipeline: chain multiple shell commands with pass/fail control."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional
import os


@dataclass
class PipelineConfig:
    steps: List[str] = field(default_factory=list)
    stop_on_failure: bool = True
    label: str = "pipeline"

    def __post_init__(self) -> None:
        if not isinstance(self.stop_on_failure, bool):
            raise TypeError("stop_on_failure must be a bool")
        self.label = self.label.strip()
        if not self.label:
            raise ValueError("label must not be empty")
        self.steps = [s for s in self.steps if s.strip()]

    @classmethod
    def from_env(cls) -> "PipelineConfig":
        raw = os.environ.get("CRONWRAP_PIPELINE_STEPS", "")
        steps = [s.strip() for s in raw.split(";") if s.strip()] if raw else []
        stop = os.environ.get("CRONWRAP_PIPELINE_STOP_ON_FAILURE", "true").lower() != "false"
        label = os.environ.get("CRONWRAP_PIPELINE_LABEL", "pipeline")
        return cls(steps=steps, stop_on_failure=stop, label=label)


@dataclass
class StepResult:
    index: int
    command: str
    exit_code: int
    stdout: str
    stderr: str

    @property
    def succeeded(self) -> bool:
        return self.exit_code == 0


@dataclass
class PipelineResult:
    label: str
    step_results: List[StepResult] = field(default_factory=list)
    aborted_at: Optional[int] = None

    @property
    def succeeded(self) -> bool:
        return all(r.succeeded for r in self.step_results)

    @property
    def total_steps(self) -> int:
        return len(self.step_results)

    @property
    def passed_steps(self) -> int:
        return sum(1 for r in self.step_results if r.succeeded)

    def __str__(self) -> str:
        status = "OK" if self.succeeded else "FAILED"
        return (
            f"Pipeline '{self.label}': {status} "
            f"({self.passed_steps}/{self.total_steps} steps passed)"
        )
