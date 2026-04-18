"""Integration helpers for the watchdog module."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from cronwrap.watchdog import WatchdogConfig, WatchdogState, check_stale


def _state_path(cfg: WatchdogConfig) -> Path:
    return Path(cfg.state_dir) / f"{cfg.job_name}.json"


def load_watchdog_state(cfg: WatchdogConfig) -> WatchdogState:
    path = _state_path(cfg)
    if path.exists():
        data = json.loads(path.read_text())
        return WatchdogState.from_dict(data)
    return WatchdogState(job_name=cfg.job_name)


def save_watchdog_state(state: WatchdogState, cfg: WatchdogConfig) -> None:
    path = _state_path(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state.to_dict()))


def ping_watchdog(cfg: WatchdogConfig, now: Optional[datetime] = None) -> WatchdogState:
    """Record a successful heartbeat for the job."""
    now = now or datetime.now(timezone.utc)
    state = WatchdogState(job_name=cfg.job_name, last_seen=now, stale=False)
    save_watchdog_state(state, cfg)
    return state


def check_watchdog_or_warn(cfg: WatchdogConfig, now: Optional[datetime] = None) -> tuple[WatchdogState, bool]:
    """Load state and return (state, is_stale)."""
    state = load_watchdog_state(cfg)
    now = now or datetime.now(timezone.utc)
    stale = check_stale(state, cfg, now=now)
    state.stale = stale
    return state, stale


def build_watchdog_config() -> WatchdogConfig:
    return WatchdogConfig.from_env()
