"""Validate required environment variables before running a cron job."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class EnvValidatorConfig:
    """Configuration for environment variable validation."""

    required: List[str] = field(default_factory=list)
    """List of environment variable names that must be present and non-empty."""

    def __post_init__(self) -> None:
        cleaned: List[str] = []
        for name in self.required:
            if not isinstance(name, str) or not name.strip():
                raise ValueError("Each required env var name must be a non-empty string")
            cleaned.append(name.strip())
        self.required = cleaned

    @classmethod
    def from_env(cls) -> "EnvValidatorConfig":
        """Build config from CRONWRAP_REQUIRE_ENV (comma-separated var names)."""
        raw = os.environ.get("CRONWRAP_REQUIRE_ENV", "")
        names = [n.strip() for n in raw.split(",") if n.strip()]
        return cls(required=names)


@dataclass
class ValidationResult:
    """Result of validating required environment variables."""

    missing: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """True when no variables are missing."""
        return len(self.missing) == 0

    def __str__(self) -> str:
        if self.ok:
            return "EnvValidation: OK"
        return f"EnvValidation: MISSING {', '.join(self.missing)}"


def validate_env(config: EnvValidatorConfig) -> ValidationResult:
    """Check that every required variable is present and non-empty."""
    missing: List[str] = [
        name
        for name in config.required
        if not os.environ.get(name, "").strip()
    ]
    return ValidationResult(missing=missing)
