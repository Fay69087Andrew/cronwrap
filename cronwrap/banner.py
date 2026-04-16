"""Banner/header generation for cronwrap job output."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
import os


@dataclass
class BannerConfig:
    enabled: bool = True
    width: int = 72
    char: str = "="
    show_timestamp: bool = True
    show_pid: bool = True
    label: str = "CRONWRAP"

    def __post_init__(self) -> None:
        if self.width < 20:
            raise ValueError("width must be at least 20")
        if self.width > 200:
            raise ValueError("width must be at most 200")
        if not self.char or len(self.char) != 1:
            raise ValueError("char must be exactly one character")
        if not self.label or not self.label.strip():
            raise ValueError("label must not be empty")
        self.label = self.label.strip().upper()

    @classmethod
    def from_env(cls) -> "BannerConfig":
        enabled = os.environ.get("CRONWRAP_BANNER_ENABLED", "true").lower() != "false"
        width = int(os.environ.get("CRONWRAP_BANNER_WIDTH", "72"))
        char = os.environ.get("CRONWRAP_BANNER_CHAR", "=")
        show_timestamp = os.environ.get("CRONWRAP_BANNER_TIMESTAMP", "true").lower() != "false"
        show_pid = os.environ.get("CRONWRAP_BANNER_PID", "true").lower() != "false"
        label = os.environ.get("CRONWRAP_BANNER_LABEL", "CRONWRAP")
        return cls(
            enabled=enabled,
            width=width,
            char=char,
            show_timestamp=show_timestamp,
            show_pid=show_pid,
            label=label,
        )


def render_banner(command: str, cfg: Optional[BannerConfig] = None, now: Optional[datetime] = None) -> str:
    if cfg is None:
        cfg = BannerConfig()
    if not cfg.enabled:
        return ""
    if now is None:
        now = datetime.now(timezone.utc)

    border = cfg.char * cfg.width
    title = f" {cfg.label} "
    padded = title.center(cfg.width, cfg.char)

    lines = [border, padded, border]
    lines.append(f"  command : {command}")
    if cfg.show_timestamp:
        lines.append(f"  started : {now.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    if cfg.show_pid:
        lines.append(f"  pid     : {os.getpid()}")
    lines.append(border)
    return "\n".join(lines)
