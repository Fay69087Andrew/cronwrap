"""Helpers that wire BackoffConfig into the retry loop."""
from __future__ import annotations

import time
import logging
from typing import Callable, Optional

from cronwrap.backoff import BackoffConfig, compute_delay
from cronwrap.runner import RunResult

logger = logging.getLogger(__name__)


def run_with_backoff(
    run_fn: Callable[[], RunResult],
    max_attempts: int,
    config: Optional[BackoffConfig] = None,
    *,
    _sleep: Callable[[float], None] = time.sleep,
) -> tuple[RunResult, int]:
    """Run *run_fn* up to *max_attempts* times with exponential back-off.

    Returns a tuple of ``(final_result, attempts_made)``.
    Raises ``ValueError`` if *max_attempts* < 1.
    """
    if max_attempts < 1:
        raise ValueError(f"max_attempts must be >= 1, got {max_attempts}")

    cfg = config or BackoffConfig()
    result: RunResult | None = None

    for attempt in range(max_attempts):
        result = run_fn()
        logger.debug(
            "backoff attempt %d/%d exit_code=%s",
            attempt + 1,
            max_attempts,
            result.exit_code,
        )
        if result.success:
            return result, attempt + 1

        if attempt < max_attempts - 1:
            delay = compute_delay(attempt, cfg)
            logger.info(
                "command failed (attempt %d/%d); retrying in %.1fs",
                attempt + 1,
                max_attempts,
                delay,
            )
            _sleep(delay)

    assert result is not None
    return result, max_attempts


def backoff_summary(result: RunResult, attempts: int, max_attempts: int) -> str:
    """Return a human-readable one-line summary of a back-off run."""
    status = "succeeded" if result.success else "failed"
    return (
        f"Job {status} after {attempts}/{max_attempts} attempt(s) "
        f"(exit_code={result.exit_code})"
    )
