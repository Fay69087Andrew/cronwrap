"""Integration helpers that connect CircuitBreaker to the cronwrap runner."""

from __future__ import annotations

from typing import Optional

from cronwrap.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from cronwrap.runner import RunResult


def check_circuit_or_abort(cb: CircuitBreaker) -> None:
    """Raise SystemExit if the circuit is currently open."""
    if cb.is_open():
        state = cb.current_state()
        raise SystemExit(
            f"[cronwrap] Circuit breaker OPEN for job '{cb.job_name}' "
            f"after {state.consecutive_failures} consecutive failure(s). "
            f"Skipping execution."
        )


def update_circuit_from_result(cb: CircuitBreaker, result: RunResult) -> None:
    """Record success or failure based on the RunResult exit code."""
    if result.success:
        cb.record_success()
    else:
        cb.record_failure()


def circuit_summary(cb: CircuitBreaker) -> str:
    """Return a human-readable summary of the current circuit state."""
    state = cb.current_state()
    lines = [
        f"job          : {cb.job_name}",
        f"status       : {state.status}",
        f"failures     : {state.consecutive_failures}",
        f"threshold    : {cb.config.failure_threshold}",
        f"recovery (s) : {cb.config.recovery_timeout}",
    ]
    if state.opened_at is not None:
        import time
        elapsed = int(time.time() - state.opened_at)
        lines.append(f"open for (s) : {elapsed}")
    return "\n".join(lines)


def build_circuit_breaker(
    job_name: str,
    config: Optional[CircuitBreakerConfig] = None,
) -> CircuitBreaker:
    """Convenience factory; reads config from environment when not supplied."""
    if config is None:
        config = CircuitBreakerConfig.from_env()
    return CircuitBreaker(job_name=job_name, config=config)
