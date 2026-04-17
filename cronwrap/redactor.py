"""Redact sensitive values from command output and log lines."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import List

_DEFAULT_PATTERNS = [
    r"(?i)(password|passwd|secret|token|api[_-]?key|auth)[=:\s]+\S+",
]

_REDACTED = "[REDACTED]"


@dataclass
class RedactorConfig:
    """Configuration for the output redactor."""

    enabled: bool = True
    extra_patterns: List[str] = field(default_factory=list)
    placeholder: str = _REDACTED

    def __post_init__(self) -> None:
        if not self.placeholder:
            raise ValueError("placeholder must not be empty")
        # Validate that all patterns compile.
        for pat in self.extra_patterns:
            try:
                re.compile(pat)
            except re.error as exc:
                raise ValueError(f"Invalid redactor pattern {pat!r}: {exc}") from exc

    @classmethod
    def from_env(cls) -> "RedactorConfig":
        enabled = os.environ.get("CRONWRAP_REDACT_ENABLED", "true").lower() != "false"
        placeholder = os.environ.get("CRONWRAP_REDACT_PLACEHOLDER", _REDACTED)
        raw = os.environ.get("CRONWRAP_REDACT_PATTERNS", "")
        extra = [p.strip() for p in raw.split(",") if p.strip()] if raw.strip() else []
        return cls(enabled=enabled, extra_patterns=extra, placeholder=placeholder)


def _compiled_patterns(config: RedactorConfig) -> List[re.Pattern]:
    """Return compiled regex patterns for the given config."""
    return [re.compile(p) for p in _DEFAULT_PATTERNS + config.extra_patterns]


def redact(text: str, config: RedactorConfig | None = None) -> str:
    """Return *text* with sensitive values replaced by the placeholder.

    When *config* is ``None`` a default :class:`RedactorConfig` is used.
    """
    if config is None:
        config = RedactorConfig()
    if not config.enabled:
        return text

    result = text
    for pattern in _compiled_patterns(config):
        result = pattern.sub(config.placeholder, result)
    return result


def redact_args(args: List[str], config: RedactorConfig | None = None) -> List[str]:
    """Return a copy of *args* with each element passed through :func:`redact`.

    Useful for sanitising command-line argument lists before logging.
    """
    if config is None:
        config = RedactorConfig()
    return [redact(arg, config) for arg in args]
