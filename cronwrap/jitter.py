"""Jitter support for retry delays to avoid thundering-herd problems."""
from __future__ import annotations

import os
import random
from dataclasses import dataclass, field

_STRATEGIES = ("none", "full", "equal", "decorrelated")


@dataclass
class JitterConfig:
    """Configuration for delay jitter."""

    strategy: str = "full"
    max_jitter: float = 5.0  # seconds; caps the random component
    seed: int | None = None  # None → truly random

    def __post_init__(self) -> None:
        self.strategy = self.strategy.lower()
        if self.strategy not in _STRATEGIES:
            raise ValueError(
                f"strategy must be one of {_STRATEGIES}, got {self.strategy!r}"
            )
        if self.max_jitter < 0:
            raise ValueError(f"max_jitter must be >= 0, got {self.max_jitter}")

    @classmethod
    def from_env(cls) -> "JitterConfig":
        strategy = os.environ.get("CRONWRAP_JITTER_STRATEGY", "full")
        max_jitter = float(os.environ.get("CRONWRAP_JITTER_MAX", "5.0"))
        seed_raw = os.environ.get("CRONWRAP_JITTER_SEED")
        seed = int(seed_raw) if seed_raw is not None else None
        return cls(strategy=strategy, max_jitter=max_jitter, seed=seed)


def apply_jitter(base_delay: float, cfg: JitterConfig, _rng: random.Random | None = None) -> float:
    """Return *base_delay* adjusted according to *cfg*.

    Parameters
    ----------
    base_delay:
        The computed delay before jitter (seconds, >= 0).
    cfg:
        Jitter configuration.
    _rng:
        Optional :class:`random.Random` instance (used in tests for
        determinism).  When *None* a fresh instance is created, optionally
        seeded by ``cfg.seed``.

    Returns
    -------
    float
        The jittered delay in seconds, always >= 0.
    """
    if base_delay < 0:
        raise ValueError(f"base_delay must be >= 0, got {base_delay}")

    if cfg.strategy == "none":
        return base_delay

    rng = _rng if _rng is not None else random.Random(cfg.seed)
    cap = min(base_delay, cfg.max_jitter) if cfg.max_jitter > 0 else 0.0

    if cfg.strategy == "full":
        # Uniform in [0, base_delay] but capped by max_jitter
        return rng.uniform(0, cap) if cap > 0 else 0.0

    if cfg.strategy == "equal":
        # Half deterministic, half random
        half = base_delay / 2.0
        jitter_part = rng.uniform(0, min(half, cfg.max_jitter))
        return half + jitter_part

    if cfg.strategy == "decorrelated":
        # Each delay is random between base and 3× previous (simplified here)
        upper = min(base_delay * 3, base_delay + cfg.max_jitter)
        return rng.uniform(base_delay, upper) if upper > base_delay else base_delay

    return base_delay  # fallback (should not reach)


def clamp_delay(delay: float, min_delay: float = 0.0, max_delay: float | None = None) -> float:
    """Clamp *delay* to the range [*min_delay*, *max_delay*].

    Useful for ensuring that a jittered delay does not fall below zero or
    exceed a hard upper bound before passing it to a sleep call.

    Parameters
    ----------
    delay:
        The delay value to clamp (seconds).
    min_delay:
        Lower bound (default ``0.0``).
    max_delay:
        Upper bound, or ``None`` for no upper bound.
    """
    if min_delay < 0:
        raise ValueError(f"min_delay must be >= 0, got {min_delay}")
    if max_delay is not None and max_delay < min_delay:
        raise ValueError(
            f"max_delay ({max_delay}) must be >= min_delay ({min_delay})"
        )
    result = max(min_delay, delay)
    if max_delay is not None:
        result = min(max_delay, result)
    return result
