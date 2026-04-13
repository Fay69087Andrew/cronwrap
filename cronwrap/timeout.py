"""Timeout enforcement for wrapped cron commands."""

from __future__ import annotations

import signal
from dataclasses import dataclass, field
from typing import Optional


class TimeoutExpired(Exception):
    """Raised when a command exceeds its allowed runtime."""

    def __init__(self, seconds: int) -> None:
        self.seconds = seconds
        super().__init__(f"Command timed out after {seconds}s")


@dataclass
class TimeoutConfig:
    """Configuration for command timeout behaviour."""

    seconds: Optional[int] = None  # None means no timeout
    kill_on_expire: bool = True

    def __post_init__(self) -> None:
        if self.seconds is not None and self.seconds <= 0:
            raise ValueError("timeout seconds must be a positive integer")

    @classmethod
    def from_env(cls, env: dict) -> "TimeoutConfig":
        """Build a TimeoutConfig from environment variables.

        Reads:
          CRONWRAP_TIMEOUT   – max seconds (omit or 0 to disable)
          CRONWRAP_TIMEOUT_KILL – '0' to suppress SIGKILL on expiry
        """
        raw = env.get("CRONWRAP_TIMEOUT", "0").strip()
        seconds: Optional[int] = int(raw) if raw and int(raw) > 0 else None
        kill = env.get("CRONWRAP_TIMEOUT_KILL", "1").strip() != "0"
        return cls(seconds=seconds, kill_on_expire=kill)


class _TimeoutContext:
    """Context manager that raises TimeoutExpired via SIGALRM."""

    def __init__(self, config: TimeoutConfig) -> None:
        self._config = config
        self._previous: Optional[signal.Handlers] = None

    def _handler(self, signum: int, frame: object) -> None:  # noqa: ARG002
        raise TimeoutExpired(self._config.seconds)  # type: ignore[arg-type]

    def __enter__(self) -> "_TimeoutContext":
        if self._config.seconds is not None:
            self._previous = signal.signal(signal.SIGALRM, self._handler)
            signal.alarm(self._config.seconds)
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> bool:
        if self._config.seconds is not None:
            signal.alarm(0)  # cancel any pending alarm
            if self._previous is not None:
                signal.signal(signal.SIGALRM, self._previous)
        return False  # never suppress exceptions


def timeout_context(config: TimeoutConfig) -> _TimeoutContext:
    """Return a context manager that enforces *config.seconds* at runtime."""
    return _TimeoutContext(config)
