"""Integration helpers for snapshot feature."""
from __future__ import annotations

from cronwrap.runner import RunResult
from cronwrap.snapshot import Snapshot, SnapshotConfig, SnapshotStore


def build_snapshot_store(config: SnapshotConfig | None = None) -> SnapshotStore:
    """Build a SnapshotStore from config or environment."""
    if config is None:
        config = SnapshotConfig.from_env()
    return SnapshotStore(config)


def record_snapshot(store: SnapshotStore, job: str, result: RunResult) -> Snapshot | None:
    """Record a snapshot of the combined output from a RunResult.

    Returns None when snapshotting is not applicable (empty output).
    """
    combined = (result.stdout or "") + (result.stderr or "")
    return store.record(job, combined)


def snapshot_summary(snap: Snapshot | None) -> str:
    """Return a human-readable summary line for the snapshot."""
    if snap is None:
        return "snapshot: no output captured"
    status = "CHANGED" if snap.changed else "unchanged"
    return f"snapshot: {status} (digest={snap.digest[:12]})"


def output_changed(store: SnapshotStore, job: str, result: RunResult) -> bool:
    """Return True if the job output differs from the last recorded snapshot."""
    snap = record_snapshot(store, job, result)
    return snap.changed if snap is not None else True
