# Checkpoint

The checkpoint module lets long-running cron jobs persist progress markers so
they can **resume from where they left off** after a failure, rather than
restarting from scratch.

## How it works

1. Before each logical unit of work, call `commit_checkpoint` to save progress.
2. At startup, call `resume_or_start` to retrieve the last saved marker.
3. After the job finishes, call `finalize_checkpoint`; on success the checkpoint
   is cleared automatically.

## Configuration

| Environment variable | Default | Description |
|---|---|---|
| `CRONWRAP_CHECKPOINT_ENABLED` | `false` | Enable checkpoint persistence |
| `CRONWRAP_CHECKPOINT_DIR` | `/tmp/cronwrap/checkpoints` | Directory for checkpoint files |
| `CRONWRAP_CHECKPOINT_TTL` | `86400` | Seconds before a checkpoint is considered stale |

## Quick start

```python
from cronwrap.checkpoint import CheckpointConfig, CheckpointStore
from cronwrap.checkpoint.integration import (
    resume_or_start, commit_checkpoint, finalize_checkpoint
)

cfg = CheckpointConfig(enabled=True, state_dir="/var/run/cronwrap", ttl_seconds=3600)
store = CheckpointStore(cfg)

data = resume_or_start(store, "my-etl-job") or {"offset": 0}

for batch in fetch_batches(start=data["offset"]):
    process(batch)
    data["offset"] += len(batch)
    commit_checkpoint(store, "my-etl-job", data)

finalize_checkpoint(store, "my-etl-job", result)
```

## Stale checkpoints

Checkpoints older than `ttl_seconds` are silently discarded on the next load.
This prevents a stale marker from causing an infinite resume loop when the
underlying data has changed.

## File format

Each checkpoint is stored as a single JSON file named after the job ID
(with `/` and spaces replaced by `_`).  The schema is:

```json
{"job_id": "my-etl-job", "data": {"offset": 120}, "saved_at": 1718000000.0}
```
