"""Output formatter for cronwrap run summaries."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
import os

_VALID_FORMATS = {"text", "json", "compact"}


@dataclass
class FormatterConfig:
    format: str = "text"
    show_timestamps: bool = True
    show_command: bool = True
    indent: int = 2
    color: bool = False

    def __post_init__(self) -> None:
        self.format = self.format.lower().strip()
        if self.format not in _VALID_FORMATS:
            raise ValueError(f"format must be one of {sorted(_VALID_FORMATS)}, got {self.format!r}")
        if self.indent < 0:
            raise ValueError("indent must be >= 0")
        if self.indent > 8:
            raise ValueError("indent must be <= 8")

    @classmethod
    def from_env(cls) -> "FormatterConfig":
        return cls(
            format=os.environ.get("CRONWRAP_FORMAT", "text"),
            show_timestamps=os.environ.get("CRONWRAP_FORMAT_TIMESTAMPS", "true").lower() == "true",
            show_command=os.environ.get("CRONWRAP_FORMAT_COMMAND", "true").lower() == "true",
            indent=int(os.environ.get("CRONWRAP_FORMAT_INDENT", "2")),
            color=os.environ.get("CRONWRAP_FORMAT_COLOR", "false").lower() == "true",
        )


def format_result(cfg: FormatterConfig, result, timestamp: Optional[str] = None) -> str:
    """Format a RunResult into a human-readable or machine-readable string."""
    import json as _json

    status = "OK" if result.success else "FAIL"
    parts: dict = {"status": status, "exit_code": result.exit_code}

    if cfg.show_command:
        parts["command"] = result.command
    if cfg.show_timestamps and timestamp:
        parts["timestamp"] = timestamp
    if result.stdout:
        parts["stdout"] = result.stdout
    if result.stderr:
        parts["stderr"] = result.stderr

    if cfg.format == "json":
        return _json.dumps(parts, indent=cfg.indent)

    if cfg.format == "compact":
        cmd_part = f" cmd={result.command!r}" if cfg.show_command else ""
        ts_part = f" at={timestamp}" if (cfg.show_timestamps and timestamp) else ""
        return f"[{status}]{cmd_part}{ts_part} exit={result.exit_code}"

    # text
    lines = [f"Status  : {status}", f"Exit    : {result.exit_code}"]
    if cfg.show_command:
        lines.append(f"Command : {result.command}")
    if cfg.show_timestamps and timestamp:
        lines.append(f"Time    : {timestamp}")
    if result.stdout:
        lines.append(f"Stdout  :\n{result.stdout}")
    if result.stderr:
        lines.append(f"Stderr  :\n{result.stderr}")
    return "\n".join(lines)
