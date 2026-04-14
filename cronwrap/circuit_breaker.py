"""Circuit breaker logic for cronwrap.

Prevents repeated execution of a job that has been failing consistently,
giving downstream systems time to recover.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class CircuitBreakerConfig:
    enabled: bool = False
    failure_threshold: int = 3   # consecutive failures before opening
    recovery_timeout: int = 300  # seconds before moving to half-open
    state_dir: str = "/tmp/cronwrap/circuit"

    def __post_init__(self) -> None:
        if self.failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        if self.recovery_timeout < 1:
            raise ValueError("recovery_timeout must be >= 1")
        if not self.state_dir:
            raise ValueError("state_dir must not be empty")

    @classmethod
    def from_env(cls) -> "CircuitBreakerConfig":
        enabled = os.environ.get("CRONWRAP_CB_ENABLED", "false").lower() == "true"
        threshold = int(os.environ.get("CRONWRAP_CB_FAILURE_THRESHOLD", "3"))
        timeout = int(os.environ.get("CRONWRAP_CB_RECOVERY_TIMEOUT", "300"))
        state_dir = os.environ.get("CRONWRAP_CB_STATE_DIR", "/tmp/cronwrap/circuit")
        return cls(
            enabled=enabled,
            failure_threshold=threshold,
            recovery_timeout=timeout,
            state_dir=state_dir,
        )


@dataclass
class CircuitState:
    status: str = "closed"          # closed | open | half-open
    consecutive_failures: int = 0
    opened_at: Optional[float] = None
    last_failure_at: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "consecutive_failures": self.consecutive_failures,
            "opened_at": self.opened_at,
            "last_failure_at": self.last_failure_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CircuitState":
        return cls(
            status=data.get("status", "closed"),
            consecutive_failures=data.get("consecutive_failures", 0),
            opened_at=data.get("opened_at"),
            last_failure_at=data.get("last_failure_at"),
        )


class CircuitBreaker:
    def __init__(self, job_name: str, config: CircuitBreakerConfig) -> None:
        self.job_name = job_name
        self.config = config
        Path(config.state_dir).mkdir(parents=True, exist_ok=True)
        self._path = Path(config.state_dir) / f"{job_name}.json"

    def _load(self) -> CircuitState:
        if self._path.exists():
            try:
                return CircuitState.from_dict(json.loads(self._path.read_text()))
            except (json.JSONDecodeError, KeyError):
                pass
        return CircuitState()

    def _save(self, state: CircuitState) -> None:
        self._path.write_text(json.dumps(state.to_dict()))

    def is_open(self) -> bool:
        """Return True when the circuit is open (job should be skipped)."""
        state = self._load()
        if state.status == "open":
            if state.opened_at is not None:
                elapsed = time.time() - state.opened_at
                if elapsed >= self.config.recovery_timeout:
                    state.status = "half-open"
                    self._save(state)
                    return False
            return True
        return False

    def record_success(self) -> None:
        state = self._load()
        state.status = "closed"
        state.consecutive_failures = 0
        state.opened_at = None
        self._save(state)

    def record_failure(self) -> None:
        state = self._load()
        state.consecutive_failures += 1
        state.last_failure_at = time.time()
        if state.consecutive_failures >= self.config.failure_threshold:
            if state.status != "open":
                state.status = "open"
                state.opened_at = time.time()
        self._save(state)

    def current_state(self) -> CircuitState:
        return self._load()
