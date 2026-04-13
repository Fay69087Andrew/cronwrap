# Audit Logging

Cronwrap can record every job execution to a structured, newline-delimited JSON
audit log. This provides a durable, queryable history of **what ran, when, and
whether it succeeded**.

## Enabling audit logging

Audit logging is **enabled by default**. Set the environment variable below to
disable it:

```bash
export CRONWRAP_AUDIT_ENABLED=false
```

## Configuration

| Variable | Default | Description |
|---|---|---|
| `CRONWRAP_AUDIT_ENABLED` | `true` | Enable or disable audit logging |
| `CRONWRAP_AUDIT_DIR` | `/var/log/cronwrap/audit` | Directory for audit log files |
| `CRONWRAP_AUDIT_MAX_ENTRIES` | `10000` | Max entries retained per job |

## Log format

Each execution is appended as a single JSON line to
`<audit_dir>/<job_name>.audit.jsonl`:

```json
{
  "job_name": "backup",
  "command": "/usr/bin/backup.sh",
  "exit_code": 0,
  "stdout": "Backup complete.",
  "stderr": "",
  "started_at": "2024-03-01T08:00:00+00:00",
  "finished_at": "2024-03-01T08:00:10+00:00",
  "duration_seconds": 10.0,
  "attempt": 1,
  "tags": ["prod"],
  "succeeded": true
}
```

## Generating a report

Use `AuditStore` and `render_report` programmatically:

```python
from cronwrap.audit import AuditConfig, AuditStore
from cronwrap.audit_report import render_report

store = AuditStore(AuditConfig())
entries = store.read("backup")
print(render_report("backup", entries))
```

Example output:

```
Audit Report — backup
========================================
  Total runs     : 42
  Successes      : 40
  Failures       : 2
  Success rate   : 95.2%
  Avg duration   : 8.34s
  Max duration   : 22.10s
  Last run at    : 2024-03-01 08:00:10 UTC
  Last exit code : 0

Recent runs (newest first):
  [OK]   2024-03-01 08:00:10 UTC  exit=0  dur=8.0s  attempt=1
  [FAIL] 2024-02-29 08:00:09 UTC  exit=1  dur=9.1s  attempt=3
```

## Retention

Older entries beyond `CRONWRAP_AUDIT_MAX_ENTRIES` are automatically trimmed when
a new entry is written, keeping the log file bounded in size.
