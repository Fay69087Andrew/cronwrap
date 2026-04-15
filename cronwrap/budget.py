"""Execution budget: cap total wall-clock time across multiple runs within a window."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path


class BudgetExceededError(Exception):
    """Raised when the accumulated runtime budget is exhausted."""


@dataclass
class BudgetConfig:
    max_seconds: float = 3600.0   # total allowed seconds per window
    window_seconds: float = 86400.0  # rolling window length in seconds
    state_dir: str = "/tmp/cronwrap/budget"
    enabled: bool = True

    def __post_init__(self) -> None:
        if self.max_seconds <= 0:
            raise ValueError("max_seconds must be positive")
        if self.window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        if not self.state_dir:
            raise ValueError("state_dir must not be empty")

    @classmethod
    def from_env(cls) -> "BudgetConfig":
        return cls(
            max_seconds=float(os.environ.get("CRONWRAP_BUDGET_MAX_SECONDS", 3600)),
            window_seconds=float(os.environ.get("CRONWRAP_BUDGET_WINDOW_SECONDS", 86400)),
            state_dir=os.environ.get("CRONWRAP_BUDGET_STATE_DIR", "/tmp/cronwrap/budget"),
            enabled=os.environ.get("CRONWRAP_BUDGET_ENABLED", "true").lower() == "true",
        )


@dataclass
class BudgetState:
    runs: list[dict] = field(default_factory=list)  # [{"start": float, "duration": float}]

    def to_dict(self) -> dict:
        return {"runs": self.runs}

    @classmethod
    def from_dict(cls, data: dict) -> "BudgetState":
        return cls(runs=data.get("runs", []))

    def prune(self, window_seconds: float, now: float) -> None:
        cutoff = now - window_seconds
        self.runs = [r for r in self.runs if r["start"] >= cutoff]

    def total_seconds(self) -> float:
        return sum(r["duration"] for r in self.runs)

    def record(self, duration: float, now: float | None = None) -> None:
        self.runs.append({"start": now or time.time(), "duration": duration})


def _state_path(cfg: BudgetConfig, job_name: str) -> Path:
    safe = job_name.replace("/", "_").replace(" ", "_")
    return Path(cfg.state_dir) / f"{safe}.json"


def load_budget_state(cfg: BudgetConfig, job_name: str) -> BudgetState:
    path = _state_path(cfg, job_name)
    if path.exists():
        return BudgetState.from_dict(json.loads(path.read_text()))
    return BudgetState()


def save_budget_state(cfg: BudgetConfig, job_name: str, state: BudgetState) -> None:
    path = _state_path(cfg, job_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state.to_dict()))


def check_budget(cfg: BudgetConfig, job_name: str, now: float | None = None) -> BudgetState:
    """Load state, prune old entries, raise if budget exhausted."""
    now = now or time.time()
    state = load_budget_state(cfg, job_name)
    state.prune(cfg.window_seconds, now)
    used = state.total_seconds()
    if used >= cfg.max_seconds:
        raise BudgetExceededError(
            f"Budget exhausted for '{job_name}': {used:.1f}s used of {cfg.max_seconds:.1f}s"
        )
    return state


def record_budget(cfg: BudgetConfig, job_name: str, duration: float, now: float | None = None) -> None:
    now = now or time.time()
    state = load_budget_state(cfg, job_name)
    state.prune(cfg.window_seconds, now)
    state.record(duration, now)
    save_budget_state(cfg, job_name, state)
