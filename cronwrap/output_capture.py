"""Output capture utilities for cronwrap.

Provides configurable stdout/stderr capture with optional truncation
and encoding handling for cron job output.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional

_DEFAULT_MAX_BYTES = 1024 * 1024  # 1 MiB
_DEFAULT_ENCODING = "utf-8"
_ERRORS_HANDLER = "replace"


@dataclass
class OutputCaptureConfig:
    """Configuration for output capture behaviour."""

    max_bytes: int = _DEFAULT_MAX_BYTES
    encoding: str = _DEFAULT_ENCODING
    capture_stdout: bool = True
    capture_stderr: bool = True

    def __post_init__(self) -> None:
        if self.max_bytes <= 0:
            raise ValueError(f"max_bytes must be positive, got {self.max_bytes}")
        if not self.encoding:
            raise ValueError("encoding must not be empty")

    @classmethod
    def from_env(cls) -> "OutputCaptureConfig":
        """Build config from environment variables."""
        raw_max = os.environ.get("CRONWRAP_MAX_OUTPUT_BYTES", "")
        max_bytes = int(raw_max) if raw_max.isdigit() else _DEFAULT_MAX_BYTES
        encoding = os.environ.get("CRONWRAP_OUTPUT_ENCODING", _DEFAULT_ENCODING)
        capture_stdout = os.environ.get("CRONWRAP_CAPTURE_STDOUT", "true").lower() != "false"
        capture_stderr = os.environ.get("CRONWRAP_CAPTURE_STDERR", "true").lower() != "false"
        return cls(
            max_bytes=max_bytes,
            encoding=encoding,
            capture_stdout=capture_stdout,
            capture_stderr=capture_stderr,
        )


@dataclass
class CapturedOutput:
    """Holds the decoded, possibly-truncated output from a subprocess."""

    stdout: str = ""
    stderr: str = ""
    truncated: bool = False

    def combined(self) -> str:
        """Return stdout and stderr joined by a newline (non-empty parts only)."""
        parts = [p for p in (self.stdout, self.stderr) if p]
        return "\n".join(parts)


def decode_output(
    raw_stdout: bytes,
    raw_stderr: bytes,
    config: OutputCaptureConfig,
) -> CapturedOutput:
    """Decode raw bytes into a CapturedOutput, applying truncation as needed."""
    combined_raw = b""
    if config.capture_stdout:
        combined_raw += raw_stdout
    if config.capture_stderr:
        combined_raw += raw_stderr

    truncated = len(combined_raw) > config.max_bytes

    stdout = ""
    stderr = ""

    if config.capture_stdout:
        raw = raw_stdout[: config.max_bytes]
        stdout = raw.decode(config.encoding, errors=_ERRORS_HANDLER)

    if config.capture_stderr:
        remaining = max(0, config.max_bytes - len(raw_stdout))
        raw = raw_stderr[:remaining]
        stderr = raw.decode(config.encoding, errors=_ERRORS_HANDLER)

    return CapturedOutput(stdout=stdout, stderr=stderr, truncated=truncated)
