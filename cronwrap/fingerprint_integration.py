"""High-level helpers that wire FingerprintConfig into the cronwrap run lifecycle."""

from __future__ import annotations

from typing import Optional

from cronwrap.fingerprint import (
    FingerprintConfig,
    fingerprint_summary,
    output_changed,
)
from cronwrap.runner import RunResult


def build_fingerprint_config() -> FingerprintConfig:
    """Build a FingerprintConfig from environment variables."""
    return FingerprintConfig.from_env()


def check_output_changed(
    cfg: FingerprintConfig,
    job_id: str,
    result: RunResult,
) -> bool:
    """Return True when the combined stdout+stderr of *result* has changed.

    When *cfg.enabled* is False this always returns True so downstream
    processing is never silently skipped.
    """
    combined = (result.stdout or "") + (result.stderr or "")
    return output_changed(cfg, job_id, combined)


def record_fingerprint(
    cfg: FingerprintConfig,
    job_id: str,
    result: RunResult,
) -> dict:
    """Compute, persist, and return a summary for *result*'s output."""
    combined = (result.stdout or "") + (result.stderr or "")
    return fingerprint_summary(cfg, job_id, combined)


def fingerprint_report(
    cfg: FingerprintConfig,
    job_id: str,
    result: RunResult,
) -> str:
    """Human-readable one-liner describing whether output changed."""
    if not cfg.enabled:
        return f"[fingerprint] disabled for job {job_id!r}"
    summary = record_fingerprint(cfg, job_id, result)
    status = "CHANGED" if summary["changed"] else "UNCHANGED"
    return (
        f"[fingerprint] job={job_id!r} status={status} "
        f"algorithm={summary['algorithm']} digest={summary['digest'][:12]}…"
    )
