"""Sampler: probabilistic job execution — skip runs based on a sample rate."""
from __future__ import annotations

import os
import random
from dataclasses import dataclass, field


@dataclass
class SamplerConfig:
    """Configuration for probabilistic sampling."""
    rate: float = 1.0          # 0.0 = never run, 1.0 = always run
    enabled: bool = True
    seed: int | None = None    # for deterministic testing

    def __post_init__(self) -> None:
        if not isinstance(self.enabled, bool):
            raise TypeError("enabled must be a bool")
        if not (0.0 <= self.rate <= 1.0):
            raise ValueError("rate must be between 0.0 and 1.0 inclusive")

    @classmethod
    def from_env(cls) -> "SamplerConfig":
        raw_rate = os.environ.get("CRONWRAP_SAMPLE_RATE", "1.0")
        raw_enabled = os.environ.get("CRONWRAP_SAMPLE_ENABLED", "true").lower()
        raw_seed = os.environ.get("CRONWRAP_SAMPLE_SEED", "")
        return cls(
            rate=float(raw_rate),
            enabled=raw_enabled != "false",
            seed=int(raw_seed) if raw_seed.strip() else None,
        )


def should_sample(config: SamplerConfig, rng: random.Random | None = None) -> bool:
    """Return True if this run should be executed based on the sample rate."""
    if not config.enabled:
        return True
    if config.rate >= 1.0:
        return True
    if config.rate <= 0.0:
        return False
    r = rng if rng is not None else (random.Random(config.seed) if config.seed is not None else random)
    return r.random() < config.rate


def sampler_summary(config: SamplerConfig, sampled: bool) -> str:
    """Return a human-readable summary of the sampling decision."""
    if not config.enabled:
        return "sampling disabled — job will always run"
    status = "selected" if sampled else "skipped"
    return f"sampler: rate={config.rate:.2f}, decision={status}"
