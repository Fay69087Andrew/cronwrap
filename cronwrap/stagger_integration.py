"""Integration helpers for stagger: build config and apply delay before run."""
from __future__ import annotations

import time
from typing import Callable, TypeVar

from cronwrap.stagger import StaggerConfig, compute_stagger_delay, stagger_summary

T = TypeVar("T")


def build_stagger_config() -> StaggerConfig:
    return StaggerConfig.from_env()


def apply_stagger(cfg: StaggerConfig, *, sleep_fn: Callable[[float], None] = time.sleep) -> float:
    """Compute and apply the stagger delay. Returns the delay applied."""
    delay = compute_stagger_delay(cfg)
    if delay > 0:
        sleep_fn(delay)
    return delay


def run_with_stagger(
    cfg: StaggerConfig,
    fn: Callable[[], T],
    *,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> tuple[T, str]:
    """Apply stagger delay then run fn. Returns (result, summary)."""
    delay = apply_stagger(cfg, sleep_fn=sleep_fn)
    result = fn()
    summary = stagger_summary(cfg, delay)
    return result, summary
