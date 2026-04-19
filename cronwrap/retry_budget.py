"""Retry budget: limits total retry attempts across a time window."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path


class RetryBudgetExceededError(Exception):
    pass


@dataclass
class RetryBudgetConfig:
    max_retries: int = 10
    window_seconds: int = 3600
    state_dir: str = "/tmp/cronwrap/retry_budget"
    enabled: bool = True

    def __post_init__(self) -> None:
        if self.max_retries < 1:
            raise ValueError("max_retries must be >= 1")
        if self.window_seconds <= 0:
            raise ValueError("window_seconds must be > 0")
        if not self.state_dir:
            raise ValueError("state_dir must not be empty")

    @classmethod
    def from_env(cls) -> "RetryBudgetConfig":
        return cls(
            max_retries=int(os.environ.get("CRONWRAP_RETRY_BUDGET_MAX", 10)),
            window_seconds=int(os.environ.get("CRONWRAP_RETRY_BUDGET_WINDOW", 3600)),
            state_dir=os.environ.get("CRONWRAP_RETRY_BUDGET_STATE_DIR", "/tmp/cronwrap/retry_budget"),
            enabled=os.environ.get("CRONWRAP_RETRY_BUDGET_ENABLED", "true").lower() == "true",
        )


@dataclass
class RetryBudgetState:
    attempts: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"attempts": self.attempts}

    @classmethod
    def from_dict(cls, d: dict) -> "RetryBudgetState":
        return cls(attempts=d.get("attempts", []))

    def prune(self, window_seconds: int) -> None:
        cutoff = time.time() - window_seconds
        self.attempts = [t for t in self.attempts if t >= cutoff]

    def count(self) -> int:
        return len(self.attempts)

    def record(self) -> None:
        self.attempts.append(time.time())


def _state_path(cfg: RetryBudgetConfig, job_id: str) -> Path:
    return Path(cfg.state_dir) / f"{job_id}.json"


def load_state(cfg: RetryBudgetConfig, job_id: str) -> RetryBudgetState:
    p = _state_path(cfg, job_id)
    if not p.exists():
        return RetryBudgetState()
    return RetryBudgetState.from_dict(json.loads(p.read_text()))


def save_state(cfg: RetryBudgetConfig, job_id: str, state: RetryBudgetState) -> None:
    p = _state_path(cfg, job_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state.to_dict()))


def consume_retry(cfg: RetryBudgetConfig, job_id: str) -> RetryBudgetState:
    state = load_state(cfg, job_id)
    state.prune(cfg.window_seconds)
    if state.count() >= cfg.max_retries:
        raise RetryBudgetExceededError(
            f"Retry budget exhausted: {state.count()}/{cfg.max_retries} in window"
        )
    state.record()
    save_state(cfg, job_id, state)
    return state


def budget_summary(cfg: RetryBudgetConfig, job_id: str) -> str:
    state = load_state(cfg, job_id)
    state.prune(cfg.window_seconds)
    remaining = max(0, cfg.max_retries - state.count())
    return (
        f"retry_budget job={job_id} used={state.count()} "
        f"max={cfg.max_retries} remaining={remaining} window={cfg.window_seconds}s"
    )
