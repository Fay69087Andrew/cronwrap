"""High-level helpers for integrating quota enforcement into the run pipeline."""
from __future__ import annotations

import sys
from typing import Callable

from cronwrap.quota import (
    QuotaConfig,
    QuotaExceededError,
    check_quota,
    quota_summary,
)
from cronwrap.runner import RunResult


def build_quota_config() -> QuotaConfig:
    """Build a QuotaConfig from environment variables."""
    return QuotaConfig.from_env()


def check_quota_or_abort(
    cfg: QuotaConfig,
    job_id: str,
    *,
    logger: Callable[[str], None] | None = None,
) -> None:
    """Enforce quota; call sys.exit(1) if the quota is exceeded."""
    try:
        check_quota(cfg, job_id)
    except QuotaExceededError as exc:
        msg = str(exc)
        if logger:
            logger(msg)
        else:
            print(msg, file=sys.stderr)
        sys.exit(1)


def run_with_quota(
    cfg: QuotaConfig,
    job_id: str,
    run_fn: Callable[[], RunResult],
    *,
    logger: Callable[[str], None] | None = None,
) -> tuple[RunResult, str]:
    """Run *run_fn* only if quota allows; return (result, summary)."""
    check_quota_or_abort(cfg, job_id, logger=logger)
    result = run_fn()
    summary = quota_summary(cfg, job_id)
    return result, summary
