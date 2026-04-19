"""Integration helpers for retry budget."""
from __future__ import annotations

import sys
from typing import Callable

from cronwrap.retry_budget import (
    RetryBudgetConfig,
    RetryBudgetExceededError,
    budget_summary,
    consume_retry,
)
from cronwrap.runner import RunResult


def build_retry_budget_config() -> RetryBudgetConfig:
    return RetryBudgetConfig.from_env()


def check_budget_or_abort(cfg: RetryBudgetConfig, job_id: str) -> None:
    """Consume one retry token or exit if budget exhausted."""
    if not cfg.enabled:
        return
    try:
        consume_retry(cfg, job_id)
    except RetryBudgetExceededError as exc:
        print(f"[cronwrap] {exc}", file=sys.stderr)
        sys.exit(1)


def run_with_retry_budget(
    cfg: RetryBudgetConfig,
    job_id: str,
    runner: Callable[[], RunResult],
    max_attempts: int = 1,
) -> tuple[RunResult, str]:
    """Run *runner* up to *max_attempts* times, consuming budget on each retry."""
    result: RunResult | None = None
    for attempt in range(max_attempts):
        result = runner()
        if result.success:
            break
        if attempt < max_attempts - 1:
            check_budget_or_abort(cfg, job_id)
    summary = budget_summary(cfg, job_id)
    assert result is not None
    return result, summary
