"""drain_integration.py – helpers to wire DrainConfig into the CLI pipeline."""
from __future__ import annotations

import threading
from typing import Optional

from cronwrap.drain import DrainConfig, DrainResult, drain_summary, wait_for_drain


def build_drain_config() -> DrainConfig:
    """Build a DrainConfig from environment variables."""
    return DrainConfig.from_env()


def drain_process(
    cfg: DrainConfig,
    proc,  # subprocess.Popen-like with .poll() -> Optional[int]
    *,
    _sleep=None,
    _time=None,
) -> DrainResult:
    """Wait for *proc* to finish within the drain window.

    Returns a DrainResult indicating whether the process drained cleanly.
    """
    kwargs = {}
    if _sleep is not None:
        kwargs["_sleep"] = _sleep
    if _time is not None:
        kwargs["_time"] = _time

    def is_done() -> bool:
        return proc.poll() is not None

    return wait_for_drain(cfg, is_done, **kwargs)


def report_drain(result: DrainResult) -> str:
    """Return a human-readable drain report line."""
    return drain_summary(result)
