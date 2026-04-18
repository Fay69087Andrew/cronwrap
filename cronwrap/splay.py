"""Random splay (startup delay) to spread cron jobs across a time window."""
from __future__ import annotations

import os
import random
import time
from dataclasses import dataclass, field

_DEFAULT_MAX_SPLAY = 0
_DEFAULT_ENABLED = True


@dataclass
class SplayConfig:
    max_seconds: int = 0
    enabled: bool = True
    seed: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.enabled, bool):
            raise TypeError("enabled must be a bool")
        if self.max_seconds < 0:
            raise ValueError("max_seconds must be >= 0")

    @classmethod
    def from_env(cls) -> "SplayConfig":
        enabled = os.environ.get("CRONWRAP_SPLAY_ENABLED", "true").lower() != "false"
        max_seconds = int(os.environ.get("CRONWRAP_SPLAY_MAX_SECONDS", "0"))
        raw_seed = os.environ.get("CRONWRAP_SPLAY_SEED")
        seed = int(raw_seed) if raw_seed is not None else None
        return cls(max_seconds=max_seconds, enabled=enabled, seed=seed)


def compute_splay(cfg: SplayConfig) -> float:
    """Return a random delay in seconds within [0, max_seconds]."""
    if not cfg.enabled or cfg.max_seconds == 0:
        return 0.0
    rng = random.Random(cfg.seed)
    return rng.uniform(0, cfg.max_seconds)


def apply_splay(cfg: SplayConfig, *, _sleep=time.sleep) -> float:
    """Sleep for a random splay delay and return the actual delay used."""
    delay = compute_splay(cfg)
    if delay > 0:
        _sleep(delay)
    return delay


def splay_summary(cfg: SplayConfig, delay: float) -> str:
    if not cfg.enabled or cfg.max_seconds == 0:
        return "splay: disabled"
    return f"splay: slept {delay:.2f}s (max {cfg.max_seconds}s)"
