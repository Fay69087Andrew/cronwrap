"""Integration helpers for the sampler module."""
from __future__ import annotations

import random
import sys

from cronwrap.sampler import SamplerConfig, sampler_summary, should_sample


def build_sampler_config() -> SamplerConfig:
    """Build a SamplerConfig from environment variables."""
    return SamplerConfig.from_env()


def check_sample_or_skip(config: SamplerConfig, rng: random.Random | None = None) -> bool:
    """Return True if the job should run; exit 0 silently if it should be skipped.

    Callers can treat a False return as 'already handled' (sys.exit was called),
    though in practice this function exits rather than returning False.
    """
    sampled = should_sample(config, rng=rng)
    summary = sampler_summary(config, sampled)
    if not sampled:
        print(f"[cronwrap] {summary}")
        sys.exit(0)
    return True


def run_with_sampler(
    config: SamplerConfig,
    run_fn,
    rng: random.Random | None = None,
):
    """Run *run_fn* only if the sampler selects this execution.

    Returns (result, summary) where result is None when skipped.
    """
    sampled = should_sample(config, rng=rng)
    summary = sampler_summary(config, sampled)
    if not sampled:
        return None, summary
    result = run_fn()
    return result, summary
