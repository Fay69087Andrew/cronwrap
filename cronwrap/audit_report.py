"""Generates a human-readable summary report from audit log entries."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, List, Optional

from cronwrap.audit import AuditEntry


def _pct(num: int, denom: int) -> float:
    return round(100.0 * num / denom, 1) if denom else 0.0


def _fmt_dt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")


def summarise_job(entries: List[AuditEntry]) -> Dict:
    """Return a summary dict for a single job's audit entries."""
    if not entries:
        return {}
    total = len(entries)
    successes = sum(1 for e in entries if e.succeeded)
    failures = total - successes
    durations = [e.duration_seconds for e in entries]
    last = max(entries, key=lambda e: e.finished_at)
    return {
        "total_runs": total,
        "successes": successes,
        "failures": failures,
        "success_rate": _pct(successes, total),
        "avg_duration_seconds": round(sum(durations) / total, 2),
        "max_duration_seconds": round(max(durations), 2),
        "last_run_at": last.finished_at,
        "last_exit_code": last.exit_code,
    }


def render_report(job_name: str, entries: List[AuditEntry]) -> str:
    """Render a plain-text audit report for *job_name*."""
    if not entries:
        return f"No audit entries found for job: {job_name}\n"

    s = summarise_job(entries)
    lines = [
        f"Audit Report — {job_name}",
        "=" * 40,
        f"  Total runs     : {s['total_runs']}",
        f"  Successes      : {s['successes']}",
        f"  Failures       : {s['failures']}",
        f"  Success rate   : {s['success_rate']}%",
        f"  Avg duration   : {s['avg_duration_seconds']}s",
        f"  Max duration   : {s['max_duration_seconds']}s",
        f"  Last run at    : {_fmt_dt(s['last_run_at'])}",
        f"  Last exit code : {s['last_exit_code']}",
        "",
        "Recent runs (newest first):",
    ]
    for entry in reversed(entries[-10:]):
        status = "OK" if entry.succeeded else "FAIL"
        lines.append(
            f"  [{status}] {_fmt_dt(entry.finished_at)}"
            f"  exit={entry.exit_code}"
            f"  dur={entry.duration_seconds:.1f}s"
            f"  attempt={entry.attempt}"
        )
    return "\n".join(lines) + "\n"
