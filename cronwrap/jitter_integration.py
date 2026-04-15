"""High-level helpers that combine JitterConfig with retry/backoff loops."""
from __future__ import annotations

import random
import time
from typing import Callable, Sequence

from cronwrap.jitter import JitterConfig, apply_jitter
from cronwrap.runner import RunResult


def jittered_delays(
    base_delays: Sequence[float],
    cfg: JitterConfig,
    _rng: random.Random | None = None,
) -> list[float]:
    """Apply jitter to every delay in *base_delays* and return a new list."""
    return [apply_jitter(d, cfg, _rng) for d in base_delays]


def run_with_jitter(
    command_fn: Callable[[], RunResult],
    delays: Sequence[float],
    cfg: JitterConfig,
    _sleep: Callable[[float], None] = time.sleep,
    _rng: random.Random | None = None,
) -> tuple[RunResult, list[float]]:
    """Run *command_fn*, retrying with jittered *delays* on failure.

    Returns
    -------
    (final_result, actual_delays_slept)
        The last :class:`~cronwrap.runner.RunResult` and the list of
        jittered sleep durations that were actually used.
    """
    actual_slept: list[float] = []
    result = command_fn()
    if result.success:
        return result, actual_slept

    jdelays = jittered_delays(delays, cfg, _rng)
    for delay in jdelays:
        _sleep(delay)
        actual_slept.append(delay)
        result = command_fn()
        if result.success:
            break

    return result, actual_slept


def jitter_summary(delays_slept: Sequence[float]) -> str:
    """Return a human-readable summary of jittered delays."""
    if not delays_slept:
        return "No jittered delays applied."
    total = sum(delays_slept)
    parts = ", ".join(f"{d:.2f}s" for d in delays_slept)
    return f"Jitter applied over {len(delays_slept)} attempt(s): [{parts}] (total {total:.2f}s)"
