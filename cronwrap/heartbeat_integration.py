"""Integration helpers for running a job with heartbeat pings."""

from __future__ import annotations

from typing import Callable, Optional

from cronwrap.heartbeat import HeartbeatConfig, HeartbeatWorker
from cronwrap.runner import RunResult


def run_with_heartbeat(
    config: HeartbeatConfig,
    job: Callable[[], RunResult],
    ping_fn=None,
) -> tuple[RunResult, dict]:
    """Execute *job* while sending periodic heartbeat pings.

    Returns the :class:`~cronwrap.runner.RunResult` and a summary dict.
    """
    worker = HeartbeatWorker(config, ping_fn=ping_fn)
    worker.start()
    try:
        result = job()
    finally:
        worker.stop()
    return result, worker.summary()


def heartbeat_summary(worker: HeartbeatWorker) -> str:
    """Return a human-readable summary of heartbeat activity."""
    s = worker.summary()
    lines = [
        f"Heartbeat URL : {s['url'] or '(none)'}",
        f"Interval (s)  : {s['interval']}",
        f"Pings sent    : {s['ping_count']}",
        f"Last error    : {s['last_error'] or 'none'}",
    ]
    return "\n".join(lines)


def build_heartbeat(env: bool = True, **overrides) -> HeartbeatWorker:
    """Convenience factory: load config from env then apply *overrides*."""
    cfg = HeartbeatConfig.from_env() if env else HeartbeatConfig()
    for key, value in overrides.items():
        setattr(cfg, key, value)
    return HeartbeatWorker(cfg)
