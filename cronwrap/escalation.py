"""Escalation policy: re-alert after repeated failures."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class EscalationConfig:
    enabled: bool = False
    threshold: int = 3          # failures before escalating
    interval: int = 3600        # seconds between escalation alerts
    state_dir: str = "/tmp/cronwrap/escalation"

    def __post_init__(self) -> None:
        if self.threshold < 1:
            raise ValueError("threshold must be >= 1")
        if self.interval <= 0:
            raise ValueError("interval must be > 0")
        if not self.state_dir:
            raise ValueError("state_dir must not be empty")

    @classmethod
    def from_env(cls) -> "EscalationConfig":
        return cls(
            enabled=os.environ.get("CRONWRAP_ESCALATION_ENABLED", "false").lower() == "true",
            threshold=int(os.environ.get("CRONWRAP_ESCALATION_THRESHOLD", "3")),
            interval=int(os.environ.get("CRONWRAP_ESCALATION_INTERVAL", "3600")),
            state_dir=os.environ.get("CRONWRAP_ESCALATION_STATE_DIR", "/tmp/cronwrap/escalation"),
        )


@dataclass
class EscalationState:
    consecutive_failures: int = 0
    last_escalated_at: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "consecutive_failures": self.consecutive_failures,
            "last_escalated_at": self.last_escalated_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "EscalationState":
        return cls(
            consecutive_failures=d.get("consecutive_failures", 0),
            last_escalated_at=d.get("last_escalated_at"),
        )


def _state_path(cfg: EscalationConfig, job: str) -> Path:
    return Path(cfg.state_dir) / f"{job}.json"


def load_state(cfg: EscalationConfig, job: str) -> EscalationState:
    p = _state_path(cfg, job)
    if not p.exists():
        return EscalationState()
    try:
        return EscalationState.from_dict(json.loads(p.read_text()))
    except Exception:
        return EscalationState()


def save_state(cfg: EscalationConfig, job: str, state: EscalationState) -> None:
    p = _state_path(cfg, job)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state.to_dict()))


def evaluate_escalation(cfg: EscalationConfig, job: str, succeeded: bool, now: Optional[float] = None) -> bool:
    """Update state and return True if an escalation alert should be sent."""
    if not cfg.enabled:
        return False
    now = now or time.time()
    state = load_state(cfg, job)
    if succeeded:
        state.consecutive_failures = 0
        state.last_escalated_at = None
        save_state(cfg, job, state)
        return False
    state.consecutive_failures += 1
    if state.consecutive_failures < cfg.threshold:
        save_state(cfg, job, state)
        return False
    if state.last_escalated_at is None or (now - state.last_escalated_at) >= cfg.interval:
        state.last_escalated_at = now
        save_state(cfg, job, state)
        return True
    save_state(cfg, job, state)
    return False


def escalation_summary(cfg: EscalationConfig, job: str) -> str:
    state = load_state(cfg, job)
    return (
        f"escalation job={job} enabled={cfg.enabled} "
        f"consecutive_failures={state.consecutive_failures} "
        f"threshold={cfg.threshold}"
    )
