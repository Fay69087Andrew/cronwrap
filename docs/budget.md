# Execution Budget

The **budget** module lets you cap the total wall-clock time a cron job may
consume within a rolling time window.  If the accumulated runtime exceeds the
configured maximum, the next invocation is aborted before the command is even
started.

## Configuration

| Environment variable | Default | Description |
|---|---|---|
| `CRONWRAP_BUDGET_MAX_SECONDS` | `3600` | Maximum total seconds allowed per window |
| `CRONWRAP_BUDGET_WINDOW_SECONDS` | `86400` | Rolling window length in seconds (default: 24 h) |
| `CRONWRAP_BUDGET_STATE_DIR` | `/tmp/cronwrap/budget` | Directory where per-job state files are stored |
| `CRONWRAP_BUDGET_ENABLED` | `true` | Set to `false` to disable budget enforcement |

## How it works

1. Before running the job, `check_budget_or_abort` loads the persisted state
   for that job, prunes entries older than `window_seconds`, and sums the
   remaining durations.  If the total meets or exceeds `max_seconds` a
   `SystemExit` is raised.
2. After the job finishes, `record_budget` appends the measured wall-clock
   duration to the state file so future runs can account for it.

State is stored as a JSON file named after the job (special characters
replaced with underscores) inside `state_dir`.

## Programmatic usage

```python
from cronwrap.budget import BudgetConfig
from cronwrap.budget_integration import run_with_budget

cfg = BudgetConfig(max_seconds=600, window_seconds=3600)
result, summary = run_with_budget(cfg, "my-job", lambda: run_command("./work.sh"))
print(summary)
```

## Integration with the CLI

When `CRONWRAP_BUDGET_ENABLED=true` the CLI automatically checks and records
the budget for every wrapped command.  The job name defaults to the command
string but can be overridden with `--job-name`.
