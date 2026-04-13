# Job Execution History

`cronwrap` can record the outcome of every job run to a local JSON file,
giving you a lightweight audit trail without requiring an external database.

## Storage

By default history is written to `~/.cronwrap_history.json`.  
Override this with the `CRONWRAP_HISTORY_FILE` environment variable or by
passing `--history-file` on the CLI.

```
export CRONWRAP_HISTORY_FILE=/var/log/cronwrap/history.json
```

## Entry format

Each entry is a JSON object:

```json
{
  "command": "pg_dump mydb | gzip > /backups/mydb.gz",
  "exit_code": 0,
  "started_at": "2024-06-15T03:00:01+00:00",
  "duration_seconds": 4.217,
  "attempts": 1,
  "stdout": "",
  "stderr": ""
}
```

| Field              | Description                                      |
|--------------------|--------------------------------------------------|
| `command`          | The full command that was executed               |
| `exit_code`        | Final exit code (after all retry attempts)       |
| `started_at`       | UTC ISO-8601 timestamp of the first attempt      |
| `duration_seconds` | Wall-clock time across all attempts              |
| `attempts`         | Number of attempts made (see retry config)       |
| `stdout`           | Captured standard output (may be truncated)      |
| `stderr`           | Captured standard error  (may be truncated)      |

## Retention

The store keeps the **last 100 entries** by default.  
Adjust this with `CRONWRAP_HISTORY_MAX_ENTRIES`.

## Disabling history

Set `CRONWRAP_HISTORY_FILE=` (empty string) to skip writing history entirely.
