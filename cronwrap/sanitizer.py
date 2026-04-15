"""Output sanitizer: strips ANSI escape codes and non-printable characters from job output."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# Matches ANSI CSI escape sequences (colours, cursor movement, etc.)
_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
# Matches other ESC-based sequences (OSC, etc.)
_ESC_RE = re.compile(r"\x1b[^\x1b]*")
# Matches non-printable ASCII except tab (\x09) and newline (\x0a)
_NON_PRINTABLE_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


@dataclass
class SanitizerConfig:
    """Configuration for the output sanitizer."""

    strip_ansi: bool = True
    strip_non_printable: bool = True
    max_length: int = 0  # 0 means unlimited
    replacement: str = ""

    def __post_init__(self) -> None:
        if self.max_length < 0:
            raise ValueError("max_length must be >= 0")
        if not isinstance(self.replacement, str):
            raise TypeError("replacement must be a str")

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "SanitizerConfig":
        import os

        e = env if env is not None else os.environ
        strip_ansi = e.get("CRONWRAP_SANITIZE_ANSI", "true").lower() not in ("0", "false", "no")
        strip_np = e.get("CRONWRAP_SANITIZE_NON_PRINTABLE", "true").lower() not in ("0", "false", "no")
        max_length = int(e.get("CRONWRAP_SANITIZE_MAX_LENGTH", "0"))
        replacement = e.get("CRONWRAP_SANITIZE_REPLACEMENT", "")
        return cls(
            strip_ansi=strip_ansi,
            strip_non_printable=strip_np,
            max_length=max_length,
            replacement=replacement,
        )


def sanitize(text: str, cfg: SanitizerConfig | None = None) -> str:
    """Return *text* with ANSI codes and/or non-printable characters removed.

    Args:
        text: The raw string to sanitize.
        cfg:  A :class:`SanitizerConfig`; defaults to ``SanitizerConfig()``.

    Returns:
        Sanitized string, optionally truncated to ``cfg.max_length`` characters.
    """
    if cfg is None:
        cfg = SanitizerConfig()

    result = text
    if cfg.strip_ansi:
        result = _ANSI_ESCAPE_RE.sub(cfg.replacement, result)
        result = _ESC_RE.sub(cfg.replacement, result)
    if cfg.strip_non_printable:
        result = _NON_PRINTABLE_RE.sub(cfg.replacement, result)
    if cfg.max_length > 0 and len(result) > cfg.max_length:
        result = result[: cfg.max_length]
    return result
