"""High-level helpers for job roster integration."""
from __future__ import annotations

import os
from typing import Dict, Optional

from cronwrap.roster import RosterConfig, RosterEntry, RosterStore


def build_roster_config() -> RosterConfig:
    return RosterConfig.from_env()


def ensure_registered(
    store: RosterStore,
    job_id: str,
    command: str,
    tags: Optional[Dict[str, str]] = None,
) -> RosterEntry:
    """Register the job if not already present, then touch last_seen."""
    entry = store.get(job_id)
    if entry is None:
        entry = RosterEntry(job_id=job_id, command=command, tags=tags or {})
        store.register(entry)
    else:
        store.touch(job_id)
    return store.get(job_id)  # type: ignore[return-value]


def roster_summary(store: RosterStore) -> str:
    jobs = store.list_jobs()
    if not jobs:
        return "roster: no jobs registered"
    lines = [f"roster: {len(jobs)} job(s) registered"]
    for e in sorted(jobs, key=lambda x: x.job_id):
        seen = f"{e.last_seen:.0f}" if e.last_seen else "never"
        lines.append(f"  {e.job_id}: cmd={e.command!r} last_seen={seen}")
    return "\n".join(lines)
