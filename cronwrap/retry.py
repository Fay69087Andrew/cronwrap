"""Retry logic for cronwrap — re-runs failed commands up to a configurable limit."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from cronwrap.runner import RunResult, run_command


@dataclass
class RetryConfig:
    """Configuration for retry behaviour."""

    max_attempts: int = 1          # total attempts (1 = no retry)
    delay_seconds: float = 0.0    # wait between attempts
    backoff_factor: float = 1.0   # multiply delay by this after each failure

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.delay_seconds < 0:
            raise ValueError("delay_seconds must be >= 0")
        if self.backoff_factor < 1.0:
            raise ValueError("backoff_factor must be >= 1.0")


@dataclass
class RetryResult:
    """Outcome of a (possibly retried) command execution."""

    attempts: List[RunResult] = field(default_factory=list)

    @property
    def final(self) -> RunResult:
        """The last attempt's result."""
        return self.attempts[-1]

    @property
    def succeeded(self) -> bool:
        return self.final.success

    @property
    def total_attempts(self) -> int:
        return len(self.attempts)

    def __str__(self) -> str:
        status = "succeeded" if self.succeeded else "failed"
        return (
            f"RetryResult({status}, "
            f"attempts={self.total_attempts}, "
            f"exit_code={self.final.exit_code})"
        )


def run_with_retry(
    command: str,
    config: Optional[RetryConfig] = None,
    *,
    _sleep: Callable[[float], None] = time.sleep,
) -> RetryResult:
    """Run *command*, retrying on failure according to *config*.

    Parameters
    ----------
    command:
        Shell command string to execute.
    config:
        Retry settings; defaults to a single attempt with no delay.
    _sleep:
        Injectable sleep callable (used in tests to avoid real waits).
    """
    if config is None:
        config = RetryConfig()

    result = RetryResult()
    delay = config.delay_seconds

    for attempt in range(1, config.max_attempts + 1):
        run_result = run_command(command)
        result.attempts.append(run_result)

        if run_result.success:
            break

        if attempt < config.max_attempts:
            if delay > 0:
                _sleep(delay)
            delay *= config.backoff_factor

    return result
