"""Output trimmer: drop leading/trailing blank lines and normalize whitespace."""
from __future__ import annotations

from dataclasses import dataclass, field
import os


@dataclass
class TrimmerConfig:
    enabled: bool = True
    strip_leading_blank_lines: bool = True
    strip_trailing_blank_lines: bool = True
    collapse_blank_lines: bool = False  # collapse multiple blanks into one
    max_consecutive_blank: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.enabled, bool):
            raise TypeError("enabled must be a bool")
        if self.max_consecutive_blank < 1:
            raise ValueError("max_consecutive_blank must be >= 1")

    @classmethod
    def from_env(cls) -> "TrimmerConfig":
        enabled = os.getenv("CRONWRAP_TRIMMER_ENABLED", "true").lower() == "true"
        strip_lead = os.getenv("CRONWRAP_TRIMMER_STRIP_LEADING", "true").lower() == "true"
        strip_trail = os.getenv("CRONWRAP_TRIMMER_STRIP_TRAILING", "true").lower() == "true"
        collapse = os.getenv("CRONWRAP_TRIMMER_COLLAPSE_BLANK", "false").lower() == "true"
        max_consec = int(os.getenv("CRONWRAP_TRIMMER_MAX_CONSECUTIVE_BLANK", "1"))
        return cls(
            enabled=enabled,
            strip_leading_blank_lines=strip_lead,
            strip_trailing_blank_lines=strip_trail,
            collapse_blank_lines=collapse,
            max_consecutive_blank=max_consec,
        )


def trim_output(text: str, cfg: TrimmerConfig | None = None) -> str:
    """Apply trimming rules to *text* and return the result."""
    if cfg is None:
        cfg = TrimmerConfig()
    if not cfg.enabled:
        return text

    lines = text.splitlines()

    if cfg.strip_leading_blank_lines:
        while lines and lines[0].strip() == "":
            lines.pop(0)

    if cfg.strip_trailing_blank_lines:
        while lines and lines[-1].strip() == "":
            lines.pop()

    if cfg.collapse_blank_lines:
        collapsed: list[str] = []
        consecutive = 0
        for line in lines:
            if line.strip() == "":
                consecutive += 1
                if consecutive <= cfg.max_consecutive_blank:
                    collapsed.append(line)
            else:
                consecutive = 0
                collapsed.append(line)
        lines = collapsed

    return "\n".join(lines)


def trimmer_summary(cfg: TrimmerConfig) -> dict:
    return {
        "enabled": cfg.enabled,
        "strip_leading_blank_lines": cfg.strip_leading_blank_lines,
        "strip_trailing_blank_lines": cfg.strip_trailing_blank_lines,
        "collapse_blank_lines": cfg.collapse_blank_lines,
        "max_consecutive_blank": cfg.max_consecutive_blank,
    }
