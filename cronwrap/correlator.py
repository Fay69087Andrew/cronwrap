"""Correlation ID support for cronwrap job runs.

Each job execution can be tagged with a unique correlation ID that is
propagated through logs, alerts, and webhook payloads so that all
events for a single run can be traced together.
"""
from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field


@dataclass
class CorrelatorConfig:
    """Configuration for correlation ID generation."""

    enabled: bool = True
    prefix: str = ""
    env_var: str = "CRONWRAP_CORRELATION_ID"

    def __post_init__(self) -> None:
        if not isinstance(self.prefix, str):
            raise TypeError("prefix must be a string")
        if len(self.prefix) > 32:
            raise ValueError("prefix must be 32 characters or fewer")
        if not self.env_var:
            raise ValueError("env_var must not be empty")

    @classmethod
    def from_env(cls) -> "CorrelatorConfig":
        enabled = os.environ.get("CRONWRAP_CORRELATION_ENABLED", "true").lower() != "false"
        prefix = os.environ.get("CRONWRAP_CORRELATION_PREFIX", "")
        env_var = os.environ.get("CRONWRAP_CORRELATION_ENV_VAR", "CRONWRAP_CORRELATION_ID")
        return cls(enabled=enabled, prefix=prefix, env_var=env_var)


def generate_correlation_id(config: CorrelatorConfig) -> str:
    """Generate a new correlation ID, optionally prefixed.

    If *config.env_var* is already set in the environment, that value is
    reused so that a parent process can inject a correlation ID.
    """
    if not config.enabled:
        return ""

    existing = os.environ.get(config.env_var, "").strip()
    if existing:
        return existing

    uid = uuid.uuid4().hex
    return f"{config.prefix}{uid}" if config.prefix else uid


def correlation_summary(correlation_id: str) -> str:
    """Return a human-readable summary line for a correlation ID."""
    if not correlation_id:
        return "correlation_id=<disabled>"
    return f"correlation_id={correlation_id}"
