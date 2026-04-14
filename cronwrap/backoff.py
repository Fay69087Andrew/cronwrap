"""Exponential back-off strategy for retry delays."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List

_DEFAULT_BASE: float = 2.0
_DEFAULT_MAX_DELAY: float = 300.0  # seconds
_DEFAULT_JITTER: bool = True


@dataclass
class BackoffConfig:
    """Configuration for exponential back-off."""

    base: float = _DEFAULT_BASE
    max_delay: float = _DEFAULT_MAX_DELAY
    jitter: bool = _DEFAULT_JITTER

    def __post_init__(self) -> None:
        if self.base <= 1.0:
            raise ValueError(f"base must be > 1.0, got {self.base}")
        if self.max_delay <= 0:
            raise ValueError(f"max_delay must be > 0, got {self.max_delay}")

    @classmethod
    def from_env(cls, env: dict | None = None) -> "BackoffConfig":
        import os
        env = env or os.environ
        kwargs: dict = {}
        if "CRONWRAP_BACKOFF_BASE" in env:
            kwargs["base"] = float(env["CRONWRAP_BACKOFF_BASE"])
        if "CRONWRAP_BACKOFF_MAX_DELAY" in env:
            kwargs["max_delay"] = float(env["CRONWRAP_BACKOFF_MAX_DELAY"])
        if "CRONWRAP_BACKOFF_JITTER" in env:
            kwargs["jitter"] = env["CRONWRAP_BACKOFF_JITTER"].lower() not in ("0", "false", "no")
        return cls(**kwargs)


def compute_delay(attempt: int, config: BackoffConfig, seed: float | None = None) -> float:
    """Return the back-off delay (seconds) for *attempt* (0-indexed).

    When *jitter* is enabled a random fraction of the computed delay is
    subtracted so that concurrent jobs do not all retry simultaneously.
    The *seed* parameter is accepted only to make unit-testing deterministic.
    """
    import random

    raw = config.base ** attempt
    clamped = min(raw, config.max_delay)
    if config.jitter:
        rng = random.Random(seed)
        clamped = clamped * (0.5 + rng.random() * 0.5)
    return clamped


def delay_sequence(attempts: int, config: BackoffConfig) -> List[float]:
    """Return a list of delays for *attempts* retries (deterministic, no jitter)."""
    cfg_no_jitter = BackoffConfig(base=config.base, max_delay=config.max_delay, jitter=False)
    return [compute_delay(i, cfg_no_jitter) for i in range(attempts)]
