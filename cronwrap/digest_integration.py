"""Integration helpers for the digest module."""
from __future__ import annotations

from typing import Optional

from cronwrap.digest import DigestConfig, DigestEntry, DigestStore
from cronwrap.runner import RunResult


def build_digest_config() -> DigestConfig:
    """Build a DigestConfig from environment variables."""
    return DigestConfig.from_env()


def record_digest_entry(
    store: DigestStore,
    result: RunResult,
    duration: float,
    job_name: Optional[str] = None,
) -> DigestEntry:
    """Create a DigestEntry from a RunResult and persist it to the store."""
    name = job_name or store._cfg.job_name
    entry = DigestEntry(
        job_name=name,
        command=result.command,
        exit_code=result.exit_code,
        duration=round(duration, 3),
    )
    store.record(entry)
    return entry


def digest_summary(store: DigestStore) -> str:
    """Return a human-readable digest summary string."""
    s = store.summary()
    if s["total"] == 0:
        return "digest: no entries recorded"
    return (
        f"digest: {s['total']} runs — "
        f"{s['passed']} passed, {s['failed']} failed "
        f"({s['success_rate']}% success rate)"
    )


def flush_digest(store: DigestStore) -> dict:
    """Return the current summary and clear the store."""
    result = store.summary()
    store.clear()
    return result
