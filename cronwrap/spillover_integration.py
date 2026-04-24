"""Integration helpers that wire spillover detection into the run lifecycle."""
from __future__ import annotations

import logging
import sys
from typing import Optional

from .spillover import SpilloverConfig, SpilloverResult, check_spillover, spillover_summary

logger = logging.getLogger(__name__)


def build_spillover_config() -> SpilloverConfig:
    """Build a SpilloverConfig from environment variables."""
    return SpilloverConfig.from_env()


def evaluate_spillover(
    elapsed_seconds: float,
    cfg: Optional[SpilloverConfig] = None,
    *,
    job_name: str = "",
) -> SpilloverResult:
    """Check for spillover and emit a log warning when detected.

    If *cfg.warn_only* is False and spillover is detected, exits with code 1.
    """
    if cfg is None:
        cfg = SpilloverConfig()

    result = check_spillover(elapsed_seconds, cfg)

    if result.spilled:
        label = f"[{job_name}] " if job_name else ""
        msg = f"{label}{result}"
        if cfg.warn_only:
            logger.warning(msg)
        else:
            logger.error(msg)
            sys.exit(1)
    else:
        logger.debug(str(result))

    return result


def report_spillover(result: SpilloverResult) -> str:
    """Return a human-readable one-line report for the spillover result."""
    summary = spillover_summary(result)
    status = "SPILLED" if summary["spilled"] else "OK"
    return (
        f"spillover={status} "
        f"elapsed={summary['elapsed_seconds']:.1f}s "
        f"interval={summary['interval_seconds']:.1f}s "
        f"overflow={summary['overflow_seconds']:.1f}s"
    )
