# Debounce

The **debounce** module prevents alert fatigue by suppressing repeated
notifications for the same job within a configurable cooldown window.

## How It Works

When `should_alert()` is called for a job, cronwrap checks a small JSON state
file on disk. If a previous alert was recorded within the cooldown window the
function returns `False` and the alert is skipped. Once the window expires the
next failure triggers a fresh alert and the timestamp is updated via
`record_alert()`.

## Configuration

| Environment Variable | Default | Description |
|---|---|---|
| `CRONWRAP_DEBOUNCE_ENABLED` | `true` | Set to `false` to disable debouncing entirely |
| `CRONWRAP_DEBOUNCE_WINDOW` | `300` | Cooldown period in seconds |
| `CRONWRAP_DEBOUNCE_STATE_DIR` | `/tmp/cronwrap/debounce` | Directory where per-job state files are stored |

## Usage

```python
from cronwrap.debounce import DebounceConfig, should_alert, record_alert

cfg = DebounceConfig.from_env()
job_id = "nightly-backup"

if should_alert(cfg, job_id):
    send_alert(...)          # your alert logic
    record_alert(cfg, job_id)
```

## Programmatic Configuration

```python
cfg = DebounceConfig(
    window_seconds=600,   # 10-minute cooldown
    state_dir="/var/lib/cronwrap/debounce",
    enabled=True,
)
```

## Inspecting State

```python
from cronwrap.debounce import debounce_summary

print(debounce_summary(cfg, "nightly-backup"))
# job 'nightly-backup': last alert 42.3s ago, cooldown remaining 257.7s
```

## Notes

- Each job is identified by a `job_id` string (e.g. the command or a friendly
  name). Special characters are normalised when building the state filename.
- State files are plain JSON and can be deleted manually to reset the cooldown.
- When `enabled=False` both `should_alert()` and `record_alert()` are no-ops,
  making it safe to keep debounce calls in code even when the feature is off.
