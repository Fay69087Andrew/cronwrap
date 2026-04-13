"""Output truncation utilities for cronwrap.

Provides helpers to truncate long command output (stdout/stderr) to a
configurable maximum number of bytes or lines before it is stored or
included in alert emails.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import os

_DEFAULT_MAX_BYTES = 64 * 1024  # 64 KiB
_DEFAULT_MAX_LINES = 1000
_TRUNCATION_NOTICE = "\n... [output truncated] ..."


@dataclass
class TruncateConfig:
    """Configuration for output truncation."""

    max_bytes: int = _DEFAULT_MAX_BYTES
    max_lines: int = _DEFAULT_MAX_LINES
    enabled: bool = True

    def __post_init__(self) -> None:
        if self.max_bytes <= 0:
            raise ValueError(f"max_bytes must be positive, got {self.max_bytes}")
        if self.max_lines <= 0:
            raise ValueError(f"max_lines must be positive, got {self.max_lines}")

    @classmethod
    def from_env(cls) -> "TruncateConfig":
        """Build a TruncateConfig from environment variables.

        CRONWRAP_TRUNCATE_ENABLED  - '0' or 'false' to disable (default enabled)
        CRONWRAP_TRUNCATE_MAX_BYTES - integer byte limit (default 65536)
        CRONWRAP_TRUNCATE_MAX_LINES - integer line limit (default 1000)
        """
        enabled_raw = os.environ.get("CRONWRAP_TRUNCATE_ENABLED", "1")
        enabled = enabled_raw.strip().lower() not in ("0", "false", "no")

        max_bytes = int(os.environ.get("CRONWRAP_TRUNCATE_MAX_BYTES", str(_DEFAULT_MAX_BYTES)))
        max_lines = int(os.environ.get("CRONWRAP_TRUNCATE_MAX_LINES", str(_DEFAULT_MAX_LINES)))
        return cls(max_bytes=max_bytes, max_lines=max_lines, enabled=enabled)


def truncate_text(text: str, cfg: TruncateConfig) -> str:
    """Return *text* truncated according to *cfg*.

    Truncation is applied in two passes:
    1. Line-count limit  – keep at most ``cfg.max_lines`` lines.
    2. Byte-size limit   – keep at most ``cfg.max_bytes`` bytes (UTF-8).

    A notice is appended whenever any truncation occurs.
    """
    if not cfg.enabled or not text:
        return text

    truncated = False

    # --- line limit ---
    lines = text.splitlines(keepends=True)
    if len(lines) > cfg.max_lines:
        lines = lines[: cfg.max_lines]
        text = "".join(lines)
        truncated = True

    # --- byte limit ---
    encoded = text.encode("utf-8", errors="replace")
    if len(encoded) > cfg.max_bytes:
        encoded = encoded[: cfg.max_bytes]
        text = encoded.decode("utf-8", errors="replace")
        truncated = True

    if truncated:
        text = text.rstrip("\n") + _TRUNCATION_NOTICE

    return text
