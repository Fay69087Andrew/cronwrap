"""High-level helpers that integrate BudgetConfig with the runner pipeline."""
from __future__ import annotations

import os
import time
from typing import Callable

from cronwrap.budget import (
    BudgetConfig,
    BudgetExceededError,
    check_budget,
    record_budget,
)
from cronwrap.runner import RunResult


def build_budget_config() -> BudgetConfig:
    """Build a BudgetConfig from environment variables."""
    return BudgetConfig.from_env()


def check_budget_or_abort(cfg: BudgetConfig, job_name: str, now: float | None = None) -> None:
    """Raise SystemExit if the execution budget is exhausted."""
    if not cfg.enabled:
        return
    try:
        check_budget(cfg, job_name, now=now)
    except BudgetExceededError as exc:
        raise SystemExit(f"[cronwrap] {exc}") from exc


def run_with_budget(
    cfg: BudgetConfig,
    job_name: str,
    runner: Callable[[], RunResult],
    now: float | None = None,
) -> tuple[RunResult, str]:
    """Run *runner*, record its duration against the budget, return (result, summary)."""
    check_budget_or_abort(cfg, job_name, now=now)
    start = time.monotonic()
    result = runner()
    duration = time.monotonic() - start
    if cfg.enabled:
        record_budget(cfg, job_name, duration, now=now or time.time())
    summary = budget_summary(cfg, job_name, duration)
    return result, summary


def budget_summary(cfg: BudgetConfig, job_name: str, last_duration: float) -> str:
    """Return a human-readable one-liner describing budget usage."""
    if not cfg.enabled:
        return f"budget disabled for '{job_name}'"
    from cronwrap.budget import load_budget_state
    state = load_budget_state(cfg, job_name)
    state.prune(cfg.window_seconds, time.time())
    used = state.total_seconds()
    remaining = max(0.0, cfg.max_seconds - used)
    return (
        f"budget '{job_name}': last={last_duration:.1f}s "
        f"used={used:.1f}s/{cfg.max_seconds:.1f}s remaining={remaining:.1f}s"
    )
