# Retry Budget

The retry budget module limits the total number of retries a job can consume
within a rolling time window. This prevents runaway retry storms when a job
persistently fails.

## Configuration

| Environment Variable | Default | Description |
|---|---|---|
| `CRONWRAP_RETRY_BUDGET_MAX` | `10` | Max retries allowed in the window |
| `CRONWRAP_RETRY_BUDGET_WINDOW` | `3600` | Window size in seconds |
| `CRONWRAP_RETRY_BUDGET_STATE_DIR` | `/tmp/cronwrap/retry_budget` | Where to persist state |
| `CRONWRAP_RETRY_BUDGET_ENABLED` | `true` | Enable or disable the budget |

## Usage

```python
from cronwrap.retry_budget import RetryBudgetConfig, consume_retry, budget_summary

cfg = RetryBudgetConfig.from_env()

# Consume one retry token (raises RetryBudgetExceededError if exhausted)
consume_retry(cfg, job_id="my-job")

print(budget_summary(cfg, "my-job"))
```

## Integration Helper

```python
from cronwrap.retry_budget_integration import run_with_retry_budget, build_retry_budget_config

cfg = build_retry_budget_config()
result, summary = run_with_retry_budget(cfg, "my-job", runner_fn, max_attempts=3)
print(summary)
```

## How It Works

Each retry token is timestamped and stored in a JSON file under `state_dir`.
Before each retry, old entries outside the window are pruned. If the remaining
count meets or exceeds `max_retries`, a `RetryBudgetExceededError` is raised
and the job exits with code 1.
