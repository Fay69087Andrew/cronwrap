# Scheduler

The `cronwrap.scheduler` module lets you parse and evaluate **cron expressions**
so that your wrapper can decide whether a job is due to run, compute the next
scheduled time, or find the most recent past run.

## Requirements

```
pip install croniter
```

## Quick Start

```python
from cronwrap.scheduler import ScheduleConfig, is_due, next_run, prev_run
import datetime

cfg = ScheduleConfig(expression="0 9 * * 1")  # Every Monday at 09:00

now = datetime.datetime.utcnow()

if is_due(cfg, now=now):
    print("Job is due — running it now.")

print("Next run :", next_run(cfg, after=now))
print("Last run :", prev_run(cfg, before=now))
```

## `ScheduleConfig`

| Field        | Type  | Default       | Description                        |
|--------------|-------|---------------|------------------------------------|
| `expression` | `str` | `"* * * * *"` | Standard 5-field cron expression   |
| `timezone`   | `str` | `"UTC"`        | Timezone label (informational)     |

Passing an invalid expression raises `ValueError` immediately.

## Functions

### `is_due(config, now=None) -> bool`

Returns `True` when the cron expression matches the **current minute**.
Pass an explicit `now` datetime in tests to avoid relying on the system clock.

### `next_run(config, after=None) -> datetime`

Returns the next scheduled `datetime` after the given point in time
(defaults to `datetime.utcnow()`).

### `prev_run(config, before=None) -> datetime`

Returns the most recent scheduled `datetime` before the given point in time
(defaults to `datetime.utcnow()`).

## CLI integration

Pass `--schedule` to `cronwrap` to skip execution when the job is not due:

```
cronwrap --schedule "0 9 * * 1" -- /usr/local/bin/weekly-report.sh
```

If the current minute does not match the expression, `cronwrap` exits with
code `0` without running the wrapped command.
