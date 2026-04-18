"""Suppress specific exit codes so a job is not treated as failed."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List


@dataclass
class SuppressConfig:
    """Configuration for exit-code suppression."""

    codes: List[int] = field(default_factory=list)
    enabled: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.enabled, bool):
            raise TypeError("enabled must be a bool")
        cleaned = []
        for c in self.codes:
            if not isinstance(c, int):
                raise TypeError(f"exit code must be int, got {type(c)}")
            if c < 0:
                raise ValueError(f"exit code must be >= 0, got {c}")
            cleaned.append(c)
        self.codes = cleaned

    @classmethod
    def from_env(cls) -> "SuppressConfig":
        """Read CRONWRAP_SUPPRESS_CODES (comma-separated) and CRONWRAP_SUPPRESS_ENABLED."""
        raw_codes = os.environ.get("CRONWRAP_SUPPRESS_CODES", "")
        codes: List[int] = []
        for part in raw_codes.split(","):
            part = part.strip()
            if part:
                try:
                    codes.append(int(part))
                except ValueError:
                    raise ValueError(f"Invalid exit code in CRONWRAP_SUPPRESS_CODES: {part!r}")
        enabled_raw = os.environ.get("CRONWRAP_SUPPRESS_ENABLED", "true").lower()
        enabled = enabled_raw not in ("0", "false", "no")
        return cls(codes=codes, enabled=enabled)


def is_suppressed(config: SuppressConfig, exit_code: int) -> bool:
    """Return True if *exit_code* should be treated as success due to suppression."""
    if not config.enabled:
        return False
    return exit_code in config.codes


def suppress_summary(config: SuppressConfig) -> str:
    """Return a human-readable summary of the suppression configuration."""
    if not config.enabled or not config.codes:
        return "suppress: disabled"
    codes_str = ", ".join(str(c) for c in sorted(config.codes))
    return f"suppress: codes=[{codes_str}]"
