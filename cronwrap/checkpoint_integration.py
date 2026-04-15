"""Integration helpers for checkpoint support in cronwrap jobs."""
from __future__ import annotations

from typing import Any, Dict, Optional

from cronwrap.checkpoint import Checkpoint, CheckpointConfig, CheckpointStore
from cronwrap.runner import RunResult


def build_checkpoint_store(cfg: Optional[CheckpointConfig] = None) -> CheckpointStore:
    """Return a CheckpointStore, reading config from env if not provided."""
    if cfg is None:
        cfg = CheckpointConfig.from_env()
    return CheckpointStore(cfg)


def resume_or_start(store: CheckpointStore, job_id: str) -> Optional[Dict[str, Any]]:
    """Load existing checkpoint data for *job_id*, or None if starting fresh."""
    cp = store.load(job_id)
    if cp is not None:
        return cp.data
    return None


def commit_checkpoint(store: CheckpointStore, job_id: str, data: Dict[str, Any]) -> Checkpoint:
    """Persist *data* as the current checkpoint for *job_id*."""
    return store.save(job_id, data)


def finalize_checkpoint(store: CheckpointStore, job_id: str, result: RunResult) -> None:
    """Clear the checkpoint on success; leave it in place on failure for resume."""
    if result.success:
        store.clear(job_id)


def checkpoint_summary(cp: Optional[Checkpoint]) -> str:
    """Return a human-readable summary line for a checkpoint (or absence thereof)."""
    if cp is None:
        return "checkpoint: none"
    import time
    age = int(time.time() - cp.saved_at)
    keys = ", ".join(sorted(cp.data.keys())) or "(empty)"
    return f"checkpoint: job_id={cp.job_id} age={age}s keys=[{keys}]"
