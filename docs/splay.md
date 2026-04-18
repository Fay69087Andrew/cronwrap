# Splay

Splay adds a random startup delay before a cron job runs. This spreads load
across a window when many jobs share the same schedule.

## Configuration

| Environment Variable | Default | Description |
|---|---|---|
| `CRONWRAP_SPLAY_ENABLED` | `true` | Enable or disable splay |
| `CRONWRAP_SPLAY_MAX_SECONDS` | `0` | Upper bound of the random delay (seconds) |
| `CRONWRAP_SPLAY_SEED` | *(unset)* | Optional RNG seed for reproducible delays |

## Usage

```python
from cronwrap.splay import SplayConfig, apply_splay, splay_summary

cfg = SplayConfig.from_env()
delay = apply_splay(cfg)          # sleeps 0–max_seconds
print(splay_summary(cfg, delay))  # splay: slept 4.73s (max 30s)
```

## Behaviour

- When `max_seconds` is `0` or `enabled` is `false`, no sleep occurs.
- The delay is drawn from a uniform distribution `[0, max_seconds]`.
- Setting `CRONWRAP_SPLAY_SEED` makes the delay deterministic (useful in tests).

## Example crontab

```
* * * * * CRONWRAP_SPLAY_MAX_SECONDS=60 cronwrap -- /usr/local/bin/my-job
```

This causes the job to start between 0 and 60 seconds after the minute tick,
preventing a thundering-herd when dozens of hosts share the same crontab.
