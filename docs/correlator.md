# Correlation IDs

Cronwrap can attach a **correlation ID** to every job run. This makes it easy
to tie together log lines, alert emails, and webhook payloads that all belong
to the same execution.

## How it works

1. Before the job starts, `generate_correlation_id()` is called.
2. If the environment variable named by `env_var` (default
   `CRONWRAP_CORRELATION_ID`) is already set, that value is reused — useful
   when a parent orchestrator injects an ID.
3. Otherwise a random UUID4 hex string is generated, optionally prepended with
   `prefix`.
4. The ID travels through the run and appears in `correlation_summary()`.

## Configuration

| Environment variable | Default | Description |
|---|---|---|
| `CRONWRAP_CORRELATION_ENABLED` | `true` | Set to `false` to disable IDs entirely. |
| `CRONWRAP_CORRELATION_PREFIX` | *(empty)* | Short string prepended to every generated ID, e.g. `job-`. Max 32 chars. |
| `CRONWRAP_CORRELATION_ENV_VAR` | `CRONWRAP_CORRELATION_ID` | Name of the env var checked for an inherited ID. |

## Programmatic usage

```python
from cronwrap.correlator import CorrelatorConfig, generate_correlation_id, correlation_summary

cfg = CorrelatorConfig(prefix="nightly-")
cid = generate_correlation_id(cfg)
print(correlation_summary(cid))
# correlation_id=nightly-3f1e2a...
```

## Inheriting an ID from the environment

```bash
export CRONWRAP_CORRELATION_ID="deploy-42"
python -m cronwrap -- ./my_job.sh
# All events for this run will carry correlation_id=deploy-42
```

## Notes

- IDs are **not** persisted between runs; use `cronwrap.history` or
  `cronwrap.audit` if you need a durable record.
- The prefix is limited to 32 characters to keep IDs readable in log files.
