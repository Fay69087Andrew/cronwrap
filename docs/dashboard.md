# cronwrap Dashboard

The `cronwrap` dashboard provides a quick text-based overview of all recorded cron job runs, grouped by command.

## Usage

After jobs have run and history has been recorded (see [history.md](history.md)), you can render a dashboard summary programmatically:

```python
from cronwrap.history import HistoryStore
from cronwrap.dashboard import render_dashboard

store = HistoryStore(path="/var/log/cronwrap/history.jsonl")
print(render_dashboard(store))
```

### Example output

```
=== cronwrap dashboard ===

[OK] /usr/local/bin/backup.sh
  Runs: 10  Success: 9  Failures: 1  Rate: 90.0%
  Last run: 2024-06-01T03:00:01  Exit: 0

[FAIL] /usr/local/bin/report.py
  Runs: 5  Success: 3  Failures: 2  Rate: 60.0%
  Last run: 2024-06-01T06:00:05  Exit: 1
```

## API

### `summarise(entries) -> List[JobSummary]`

Accepts a list of `HistoryEntry` objects and returns one `JobSummary` per unique command.

### `JobSummary`

| Field | Type | Description |
|---|---|---|
| `command` | `str` | The job command |
| `total_runs` | `int` | Total number of recorded runs |
| `successes` | `int` | Runs with exit code `0` |
| `failures` | `int` | Runs with non-zero exit code |
| `last_exit_code` | `int` | Exit code of the most recent run |
| `last_ran_at` | `str` | ISO timestamp of the most recent run |
| `success_rate` | `float` | Percentage of successful runs |

### `render_dashboard(store, limit=50) -> str`

Loads up to `limit` entries from the given `HistoryStore` and returns a formatted dashboard string.
