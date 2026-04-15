"""High-level helpers that integrate ConcurrencyConfig with the run pipeline."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Callable, Optional

from cronwrap.concurrency import (
    ConcurrencyConfig,
    ConcurrencyLimitError,
    acquire_slot,
    concurrency_summary,
    release_slot,
)
from cronwrap.runner import RunResult


def build_concurrency_config() -> ConcurrencyConfig:
    """Build a ConcurrencyConfig from environment variables."""
    return ConcurrencyConfig.from_env()


def run_with_concurrency_guard(
    cfg: ConcurrencyConfig,
    job_name: str,
    run_fn: Callable[[], RunResult],
) -> tuple[RunResult, dict]:
    """Run *run_fn* only when a concurrency slot is available.

    Raises ConcurrencyLimitError if the limit is already reached.
    Always releases the slot after execution.
    """
    slot: Optional[Path] = acquire_slot(cfg, job_name)
    if slot is None:
        summary = concurrency_summary(cfg, job_name)
        raise ConcurrencyLimitError(
            f"Concurrency limit of {cfg.max_instances} reached for job '{job_name}'. "
            f"Active instances: {summary['active_instances']}"
        )
    try:
        result = run_fn()
    finally:
        release_slot(slot)

    summary = concurrency_summary(cfg, job_name)
    return result, summary


def check_concurrency_or_abort(cfg: ConcurrencyConfig, job_name: str) -> None:
    """Abort (sys.exit) if the concurrency limit is already reached.

    Intended for CLI use where raising is not appropriate.
    """
    import sys

    summary = concurrency_summary(cfg, job_name)
    if cfg.enabled and summary["active_instances"] >= cfg.max_instances:
        print(
            f"[cronwrap] concurrency limit {cfg.max_instances} reached for '{job_name}' "
            f"({summary['active_instances']} active). Skipping."
        )
        sys.exit(0)
