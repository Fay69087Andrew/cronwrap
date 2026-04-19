"""Output line prefixing for cronwrap job output."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class PrefixConfig:
    enabled: bool = True
    template: str = "[{job}]"
    include_timestamp: bool = False
    timestamp_format: str = "%Y-%m-%dT%H:%M:%S"
    job_name: str = "cronwrap"

    def __post_init__(self) -> None:
        if not isinstance(self.enabled, bool):
            raise TypeError("enabled must be a bool")
        if not self.template or not self.template.strip():
            raise ValueError("template must not be empty")
        if not self.job_name or not self.job_name.strip():
            raise ValueError("job_name must not be empty")
        self.template = self.template.strip()
        self.job_name = self.job_name.strip()

    @classmethod
    def from_env(cls) -> "PrefixConfig":
        enabled = os.environ.get("CRONWRAP_PREFIX_ENABLED", "true").lower() == "true"
        template = os.environ.get("CRONWRAP_PREFIX_TEMPLATE", "[{job}]")
        include_ts = os.environ.get("CRONWRAP_PREFIX_TIMESTAMP", "false").lower() == "true"
        ts_fmt = os.environ.get("CRONWRAP_PREFIX_TIMESTAMP_FORMAT", "%Y-%m-%dT%H:%M:%S")
        job_name = os.environ.get("CRONWRAP_JOB_NAME", "cronwrap")
        return cls(
            enabled=enabled,
            template=template,
            include_timestamp=include_ts,
            timestamp_format=ts_fmt,
            job_name=job_name,
        )


def build_prefix(cfg: PrefixConfig) -> str:
    """Build the prefix string for a single line."""
    if not cfg.enabled:
        return ""
    parts = [cfg.template.format(job=cfg.job_name)]
    if cfg.include_timestamp:
        ts = datetime.now(timezone.utc).strftime(cfg.timestamp_format)
        parts.append(ts)
    return " ".join(parts) + " "


def prefix_lines(text: str, cfg: PrefixConfig) -> str:
    """Apply prefix to every non-empty line in *text*."""
    if not cfg.enabled or not text:
        return text
    pfx = build_prefix(cfg)
    return "\n".join(
        (pfx + line) if line else line for line in text.splitlines()
    )


def prefix_summary(cfg: PrefixConfig) -> dict:
    return {
        "enabled": cfg.enabled,
        "template": cfg.template,
        "include_timestamp": cfg.include_timestamp,
        "job_name": cfg.job_name,
    }
