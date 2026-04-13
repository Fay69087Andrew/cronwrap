# Throttle

The **throttle** module lets you skip a cron job that already ran successfully within a configurable minimum interval. This is useful when a job is scheduled frequently as a safety net but should not actually execute more than once per hour (or any other window).

## How it works

1. Before running a job, `load_state` reads a small JSON file from `state_dir`.
2. `should_throttle` compares the stored `last_success_ts` against `min_interval`.
3. If the job ran successfully too recently, the wrapper skips execution and exits `0`.
4. After a successful run, `record_success` writes the current timestamp back to disk.

## Configuration

| Environment variable | Default | Description |
|---|---|---|
| `CRONWRAP_THROTTLE_ENABLED` | `true` | Set to `false` to disable throttling entirely |
| `CRONWRAP_THROTTLE_MIN_INTERVAL` | `0` | Minimum seconds between successful runs (0 = off) |
| `CRONWRAP_THROTTLE_STATE_DIR` | `/tmp/cronwrap/throttle` | Directory where per-job state files are stored |

## Usage

```python
from cronwrap.throttle import ThrottleConfig, load_state, should_throttle, record_success

cfg = ThrottleConfig.from_env()
state = load_state(cfg, job_id="my-backup")

if should_throttle(cfg, state):
    print("Skipping: job ran too recently.")
else:
    # ... run the job ...
    if result.exit_code == 0:
        record_success(cfg, job_id="my-backup")
```

## State files

Each job gets its own JSON file named after the `job_id` (with `/` and spaces replaced by `_`). Example:

```
/tmp/cronwrap/throttle/my-backup.json
```

```json
{"job_id": "my-backup", "last_success_ts": 1718000000.123}
```

The state directory is created automatically if it does not exist.

## Notes

- Only **successful** runs (exit code `0`) update the throttle timestamp.
- Failed runs do not reset the timer, so a failing job will keep retrying on every cron tick.
- Setting `min_interval` to `0` (the default) disables throttling without touching `CRONWRAP_THROTTLE_ENABLED`.
