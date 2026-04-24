"""Output line limiter — caps stdout/stderr to a configurable number of lines."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LimiterConfig:
    """Configuration for the output line limiter."""

    max_lines: int = 500
    tail: bool = True  # keep last N lines when True, first N lines when False
    enabled: bool = True
    ellipsis: str = "... (output truncated)"

    def __post_init__(self) -> None:
        if not isinstance(self.enabled, bool):
            raise TypeError("enabled must be a bool")
        if self.max_lines <= 0:
            raise ValueError("max_lines must be a positive integer")
        if not self.ellipsis:
            raise ValueError("ellipsis must be a non-empty string")

    @classmethod
    def from_env(cls) -> "LimiterConfig":
        enabled_raw = os.environ.get("CRONWRAP_LIMITER_ENABLED", "true").lower()
        enabled = enabled_raw not in {"0", "false", "no"}
        max_lines = int(os.environ.get("CRONWRAP_LIMITER_MAX_LINES", "500"))
        tail_raw = os.environ.get("CRONWRAP_LIMITER_TAIL", "true").lower()
        tail = tail_raw not in {"0", "false", "no"}
        ellipsis = os.environ.get("CRONWRAP_LIMITER_ELLIPSIS", "... (output truncated)")
        return cls(max_lines=max_lines, tail=tail, enabled=enabled, ellipsis=ellipsis)


def limit_lines(text: str, cfg: LimiterConfig) -> str:
    """Return *text* with at most ``cfg.max_lines`` lines.

    When *tail* is ``True`` the **last** N lines are kept (useful for
    retaining the most recent output); otherwise the **first** N lines
    are kept.
    """
    if not cfg.enabled or not text:
        return text

    lines = text.splitlines(keepends=True)
    if len(lines) <= cfg.max_lines:
        return text

    if cfg.tail:
        kept = lines[-cfg.max_lines :]
        return cfg.ellipsis + "\n" + "".join(kept)
    else:
        kept = lines[: cfg.max_lines]
        return "".join(kept) + "\n" + cfg.ellipsis


def limiter_summary(cfg: LimiterConfig) -> str:
    """Return a human-readable summary of the limiter configuration."""
    if not cfg.enabled:
        return "limiter disabled"
    direction = "tail" if cfg.tail else "head"
    return f"limiter enabled: max_lines={cfg.max_lines} direction={direction}"
