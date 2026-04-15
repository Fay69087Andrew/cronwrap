"""Periodic heartbeat pings to signal a job is still alive during long runs."""

from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class HeartbeatConfig:
    """Configuration for periodic heartbeat pings."""

    url: str = ""
    interval: float = 60.0  # seconds between pings
    timeout: float = 10.0   # HTTP request timeout
    enabled: bool = True

    def __post_init__(self) -> None:
        if self.interval <= 0:
            raise ValueError(f"interval must be positive, got {self.interval}")
        if self.timeout <= 0:
            raise ValueError(f"timeout must be positive, got {self.timeout}")

    @classmethod
    def from_env(cls) -> "HeartbeatConfig":
        url = os.environ.get("CRONWRAP_HEARTBEAT_URL", "")
        interval = float(os.environ.get("CRONWRAP_HEARTBEAT_INTERVAL", "60"))
        timeout = float(os.environ.get("CRONWRAP_HEARTBEAT_TIMEOUT", "10"))
        enabled = os.environ.get("CRONWRAP_HEARTBEAT_ENABLED", "true").lower() == "true"
        return cls(url=url, interval=interval, timeout=timeout, enabled=enabled)


class HeartbeatWorker:
    """Background thread that pings a URL at a fixed interval."""

    def __init__(self, config: HeartbeatConfig, ping_fn: Optional[Callable[[str, float], None]] = None) -> None:
        self._config = config
        self._ping_fn = ping_fn or _default_ping
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.ping_count: int = 0
        self.last_error: Optional[str] = None
        self.error_count: int = 0

    def start(self) -> None:
        if not self._config.enabled or not self._config.url:
            return
        self._thread = threading.Thread(target=self._run, daemon=True, name="cronwrap-heartbeat")
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=self._config.timeout + 1)

    def _run(self) -> None:
        while not self._stop_event.wait(timeout=self._config.interval):
            try:
                self._ping_fn(self._config.url, self._config.timeout)
                self.ping_count += 1
                self.last_error = None
            except Exception as exc:  # noqa: BLE001
                self.last_error = str(exc)
                self.error_count += 1

    def summary(self) -> dict:
        return {
            "url": self._config.url,
            "interval": self._config.interval,
            "ping_count": self.ping_count,
            "last_error": self.last_error,
            "error_count": self.error_count,
        }


def _default_ping(url: str, timeout: float) -> None:
    import urllib.request
    with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310
        resp.read()
