"""Graceful signal handling for cron job processes."""
from __future__ import annotations

import signal
import logging
from dataclasses import dataclass, field
from typing import Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class SignalHandlerConfig:
    """Configuration for signal handling behaviour."""

    handle_sigterm: bool = True
    handle_sigint: bool = True
    propagate_to_child: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.handle_sigterm, bool):
            raise TypeError("handle_sigterm must be a bool")
        if not isinstance(self.handle_sigint, bool):
            raise TypeError("handle_sigint must be a bool")
        if not isinstance(self.propagate_to_child, bool):
            raise TypeError("propagate_to_child must be a bool")

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "SignalHandlerConfig":
        import os
        e = env if env is not None else os.environ
        return cls(
            handle_sigterm=e.get("CRONWRAP_HANDLE_SIGTERM", "true").lower() != "false",
            handle_sigint=e.get("CRONWRAP_HANDLE_SIGINT", "true").lower() != "false",
            propagate_to_child=e.get("CRONWRAP_SIGNAL_PROPAGATE", "true").lower() != "false",
        )


@dataclass
class SignalState:
    """Tracks whether a termination signal has been received."""

    received: Optional[int] = field(default=None)

    @property
    def terminated(self) -> bool:
        return self.received is not None


def register_handlers(
    config: SignalHandlerConfig,
    state: SignalState,
    child_pid: Optional[int] = None,
    extra_callback: Optional[Callable[[int], None]] = None,
) -> None:
    """Register OS signal handlers according to *config*.

    When a signal fires the *state* object is updated and, optionally,
    the signal is forwarded to *child_pid*.
    """

    def _handler(signum: int, _frame: object) -> None:
        logger.warning("cronwrap received signal %s", signum)
        state.received = signum
        if config.propagate_to_child and child_pid is not None:
            try:
                import os
                os.kill(child_pid, signum)
            except ProcessLookupError:
                pass
        if extra_callback is not None:
            extra_callback(signum)

    if config.handle_sigterm:
        signal.signal(signal.SIGTERM, _handler)
    if config.handle_sigint:
        signal.signal(signal.SIGINT, _handler)


def signal_summary(state: SignalState) -> dict[str, object]:
    """Return a plain-dict summary of *state* suitable for logging."""
    return {
        "terminated": state.terminated,
        "signal": state.received,
    }
