# PagerDuty Alerting

cronwrap can automatically page on-call engineers via PagerDuty when a job fails.

## Configuration

All settings are controlled through environment variables:

| Variable | Default | Description |
|---|---|---|
| `CRONWRAP_PAGER_ENABLED` | `false` | Enable PagerDuty alerts |
| `CRONWRAP_PAGER_ROUTING_KEY` | `` | PagerDuty Events v2 routing key |
| `CRONWRAP_PAGER_SOURCE` | `cronwrap` | Event source identifier |
| `CRONWRAP_PAGER_SEVERITY` | `error` | Severity: `critical`, `error`, `warning`, `info` |
| `CRONWRAP_PAGER_TIMEOUT` | `10` | HTTP request timeout in seconds |

## Usage

```bash
export CRONWRAP_PAGER_ENABLED=true
export CRONWRAP_PAGER_ROUTING_KEY=your-routing-key-here

cronwrap --command "python /jobs/nightly.py"
```

If the job exits with a non-zero code, an event is sent to PagerDuty's Events v2 API.

## Payload

The alert includes:

- **summary** – human-readable failure message with the command and exit code
- **source** – configurable source label
- **severity** – configurable severity level
- **custom_details** – command, exit code, duration, and tail of stdout/stderr

## Programmatic Use

```python
from cronwrap.pager import PagerConfig
from cronwrap.pager_integration import page_on_failure

cfg = PagerConfig(enabled=True, routing_key="rk-xxx", severity="critical")
dedup_key = page_on_failure(result, config=cfg, job_name="nightly-sync")
```
