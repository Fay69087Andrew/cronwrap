"""Integration helpers for cooldown: abort or wrap job execution."""
from __future__ import annotations

import sys
import time
from typing import Callable

from cronwrap.cooldown import CooldownConfig, cooldown_summary, is_cooling_down, record_run
from cronwrap.runner import RunResult


def build_cooldown_config() -> CooldownConfig:
    return CooldownConfig.from_env()


def check_cooldown_or_abort(cfg: CooldownConfig, job_id: str, now: float | None = None) -> None:
    """Exit with code 0 (skip silently) if the job is still cooling down."""
    if is_cooling_down(cfg, job_id, now=now):
        summary = cooldown_summary(cfg, job_id, now=now)
        print(f"[cronwrap] Skipping job — cooldown active. {summary}", file=sys.stderr)
        sys.exit(0)


def run_with_cooldown(
    cfg: CooldownConfig,
    job_id: str,
    runner: Callable[[], RunResult],
    now: float | None = None,
) -> tuple[RunResult, str]:
    """Run the job and record the timestamp afterwards."""
    check_cooldown_or_abort(cfg, job_id, now=now)
    result = runner()
    ts = now if now is not None else time.time()
    record_run(cfg, job_id, now=ts)
    summary = cooldown_summary(cfg, job_id, now=ts)
    return result, summary
