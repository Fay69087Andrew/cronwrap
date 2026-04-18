# Watchdog

The watchdog module detects stale or missing cron job runs by tracking the last time a job was seen and alerting when the silence period exceeds a configured threshold.

## Overview

Unlike a timeout (which kills a running job), a watchdog watches for jobs that **fail to start** or silently disappear. If a job hasn't pinged in `max_silence_seconds`, it is marked stale.

## Configuration

| Environment Variable | Default | Description |
|---|---|---|
| `CRONWRAP_WATCHDOG_ENABLED` | `true` | Enable or disable the watchdog |
| `CRONWRAP_WATCHDOG_MAX_SILENCE` | `3600` | Seconds before a job is considered stale |
| `CRONWRAP_WATCHDOG_STATE_DIR` | `/tmp/cronwrap/watchdog` | Directory for state files |
| `CRONWRAP_JOB_NAME` | `default` | Identifies which job's state to track |

## Usage

```python
from cronwrap.watchdog_integration import (
    build_watchdog_config,
    ping_watchdog,
    check_watchdog_or_warn,
)

cfg = build_watchdog_config()

# At the start of each successful run:
ping_watchdog(cfg)

# From a monitoring script:
state, is_stale = check_watchdog_or_warn(cfg)
if is_stale:
    print(f"WARNING: {state.job_name} appears stale!")
```

## State File

State is stored as JSON in `<state_dir>/<job_name>.json`:

```json
{
  "job_name": "backup",
  "last_seen": "2024-06-01T12:00:00+00:00",
  "stale": false
}
```

## Summary

```python
from cronwrap.watchdog import watchdog_summary
print(watchdog_summary(state, cfg))
# watchdog[backup]: last_seen=2024-06-01T12:00:00+00:00 status=ok
```
