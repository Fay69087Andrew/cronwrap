"""Simple text-based dashboard for summarizing cron job history."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from cronwrap.history import HistoryEntry, HistoryStore


@dataclass
class JobSummary:
    """Aggregated statistics for a single job command."""

    command: str
    total_runs: int
    successes: int
    failures: int
    last_exit_code: int
    last_ran_at: str

    @property
    def success_rate(self) -> float:
        if self.total_runs == 0:
            return 0.0
        return self.successes / self.total_runs * 100

    def __str__(self) -> str:
        status = "OK" if self.last_exit_code == 0 else "FAIL"
        return (
            f"[{status}] {self.command}\n"
            f"  Runs: {self.total_runs}  "
            f"Success: {self.successes}  "
            f"Failures: {self.failures}  "
            f"Rate: {self.success_rate:.1f}%\n"
            f"  Last run: {self.last_ran_at}  Exit: {self.last_exit_code}"
        )


def summarise(entries: List[HistoryEntry]) -> List[JobSummary]:
    """Compute per-command summaries from a list of history entries."""
    buckets: dict[str, List[HistoryEntry]] = {}
    for entry in entries:
        buckets.setdefault(entry.command, []).append(entry)

    summaries: List[JobSummary] = []
    for command, runs in buckets.items():
        runs_sorted = sorted(runs, key=lambda e: e.ran_at)
        last = runs_sorted[-1]
        successes = sum(1 for r in runs if r.succeeded)
        summaries.append(
            JobSummary(
                command=command,
                total_runs=len(runs),
                successes=successes,
                failures=len(runs) - successes,
                last_exit_code=last.exit_code,
                last_ran_at=last.ran_at,
            )
        )
    return summaries


def render_dashboard(store: HistoryStore, limit: int = 50) -> str:
    """Return a formatted dashboard string for all recorded jobs."""
    entries = store.load(limit=limit)
    if not entries:
        return "No job history found."

    job_summaries = summarise(entries)
    lines = ["=== cronwrap dashboard ===", ""]
    for summary in job_summaries:
        lines.append(str(summary))
        lines.append("")
    return "\n".join(lines).rstrip()
