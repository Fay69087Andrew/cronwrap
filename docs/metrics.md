# Metrics

`cronwrap` collects lightweight in-process timing and outcome metrics for every
job execution without requiring an external time-series database.

## Data model

### `JobMetric`

| Field | Type | Description |
|---|---|---|
| `command` | `str` | The shell command that was run |
| `exit_code` | `int` | Process exit code (`0` = success) |
| `duration_seconds` | `float` | Wall-clock time for the execution |
| `timestamp` | `float` | Unix timestamp when the metric was created |

Convenience property `succeeded` returns `True` when `exit_code == 0`.

`to_dict()` serialises the record to a plain dictionary suitable for JSON
export or logging.

### `MetricsStore`

An in-memory accumulator that holds a list of `JobMetric` objects.

```python
from cronwrap.metrics import MetricsStore, JobMetric

store = MetricsStore()
store.record(JobMetric(command="backup.sh", exit_code=0, duration_seconds=4.2))

print(store.summary())
# {'total': 1, 'succeeded': 1, 'failed': 0, 'avg_duration': 4.2}
```

#### Methods

| Method | Description |
|---|---|
| `record(metric)` | Append a `JobMetric` |
| `all()` | Return a copy of all stored metrics |
| `for_command(cmd)` | Filter metrics by command string |
| `summary()` | Aggregate totals and average duration |
| `clear()` | Remove all stored metrics |

## Module-level store

A process-wide default store is available via `get_store()`:

```python
from cronwrap.metrics import get_store

get_store().record(metric)
print(get_store().summary())
```

The store is created lazily on first access and persists for the lifetime of
the process.
