"""Integration helpers for the profiler module."""
from __future__ import annotations

import os
from typing import Callable, Optional

from cronwrap.profiler import Profiler, ProfilerConfig, ProfileResult
from cronwrap.runner import RunResult


def build_profiler_config(env: Optional[dict] = None) -> ProfilerConfig:
    """Build a ProfilerConfig from the environment (or a supplied dict)."""
    return ProfilerConfig.from_env(env if env is not None else dict(os.environ))


def profile_result(result: RunResult, config: ProfilerConfig, label: str = "") -> ProfileResult:
    """Create a ProfileResult from an already-completed RunResult."""
    return ProfileResult(
        elapsed_seconds=result.elapsed_seconds if hasattr(result, "elapsed_seconds") else 0.0,
        warn_threshold_seconds=config.warn_threshold_seconds,
        critical_threshold_seconds=config.critical_threshold_seconds,
        label=label or result.command,
    )


def run_with_profiler(
    fn: Callable[[], RunResult],
    config: ProfilerConfig,
    label: str = "",
) -> tuple[RunResult, ProfileResult]:
    """Run *fn* inside a Profiler and return both the RunResult and ProfileResult."""
    with Profiler(config, label=label) as profiler:
        run_result = fn()
    assert profiler.result is not None
    return run_result, profiler.result


def profiler_summary(profile: ProfileResult) -> str:
    """Return a human-readable one-line summary of a ProfileResult."""
    return profile.summary()
