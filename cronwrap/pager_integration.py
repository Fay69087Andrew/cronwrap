"""High-level helpers to page on-call from a RunResult."""
from __future__ import annotations

from typing import Optional

from cronwrap.pager import PagerConfig, PagerEvent, send_page
from cronwrap.runner import RunResult


def build_pager_config() -> PagerConfig:
    return PagerConfig.from_env()


def build_event_from_result(
    result: RunResult,
    config: PagerConfig,
    job_name: str = "",
) -> PagerEvent:
    label = job_name or result.command
    summary = f"[cronwrap] Job failed: {label} (exit {result.exit_code})"
    details: dict = {
        "command": result.command,
        "exit_code": result.exit_code,
        "duration_seconds": round(result.duration, 3),
    }
    if result.stdout:
        details["stdout_tail"] = result.stdout[-500:]
    if result.stderr:
        details["stderr_tail"] = result.stderr[-500:]
    return PagerEvent(
        summary=summary,
        source=config.source,
        severity=config.severity,
        custom_details=details,
    )


def page_on_failure(
    result: RunResult,
    config: Optional[PagerConfig] = None,
    job_name: str = "",
) -> Optional[str]:
    """Send a page if the job failed. Returns dedup_key or None."""
    if config is None:
        config = build_pager_config()
    if result.success or not config.enabled:
        return None
    event = build_event_from_result(result, config, job_name=job_name)
    return send_page(config, event)


def pager_summary(dedup_key: Optional[str], config: PagerConfig) -> str:
    if not config.enabled:
        return "pager: disabled"
    if dedup_key:
        return f"pager: alert sent (dedup_key={dedup_key})"
    return "pager: no alert sent"
