# Dependency Checks

`cronwrap` can verify that prerequisite commands succeed before running a job.
If any dependency check fails, the job is skipped and a non-zero exit code is
returned.

## Configuration

All settings are controlled via environment variables.

| Variable | Default | Description |
|---|---|---|
| `CRONWRAP_DEP_CHECKS` | _(empty)_ | Comma-separated shell commands to run as checks |
| `CRONWRAP_DEP_TIMEOUT` | `10` | Seconds before a single check is considered failed |
| `CRONWRAP_DEP_ENABLED` | `true` | Set to `false` to skip all checks |

## Example

```bash
export CRONWRAP_DEP_CHECKS="pg_isready -h db, redis-cli ping"
export CRONWRAP_DEP_TIMEOUT=5

cronwrap -- python my_job.py
```

If `pg_isready` or `redis-cli ping` exits non-zero, `cronwrap` prints a
diagnostic message to stderr and exits with code `1` before running `my_job.py`.

## Programmatic usage

```python
from cronwrap.dependency import DependencyConfig, check_all, all_passed
from cronwrap.dependency_integration import run_dependency_checks_or_abort

cfg = DependencyConfig(checks=["pg_isready"], timeout_seconds=5)
results = run_dependency_checks_or_abort(cfg)  # aborts on failure
```

## Summary output

```python
from cronwrap.dependency_integration import dependency_summary
print(dependency_summary(results))
# dependency_checks: 2/2 passed
#   [OK] pg_isready
#   [OK] redis-cli ping
```
