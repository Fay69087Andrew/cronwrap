# Environment Variable Validation

`cronwrap` can verify that required environment variables are present and
non-empty **before** executing a cron job.  If any variable is missing the
job is skipped and an error is logged (or an alert is sent, depending on your
notifier configuration).

## Quick start

Set `CRONWRAP_REQUIRE_ENV` to a comma-separated list of variable names:

```bash
export CRONWRAP_REQUIRE_ENV="DATABASE_URL,SECRET_KEY,API_TOKEN"
cronwrap -- python manage.py send_digest
```

If `DATABASE_URL` is not set (or is blank) cronwrap will exit with a
non-zero status and print:

```
EnvValidation: MISSING DATABASE_URL
```

## Python API

```python
from cronwrap.env_validator import EnvValidatorConfig, validate_env

cfg = EnvValidatorConfig(required=["DATABASE_URL", "SECRET_KEY"])
result = validate_env(cfg)

if not result.ok:
    print(result)          # EnvValidation: MISSING DATABASE_URL
    raise SystemExit(1)
```

### `EnvValidatorConfig`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `required` | `list[str]` | `[]` | Variable names that must be present |

#### `from_env()` class method

Builds the config from `CRONWRAP_REQUIRE_ENV`:

```python
cfg = EnvValidatorConfig.from_env()
```

### `ValidationResult`

| Attribute | Type | Description |
|-----------|------|-------------|
| `missing` | `list[str]` | Names of absent/empty variables |
| `ok` | `bool` | `True` when `missing` is empty |

## Integration with the CLI

Validation runs automatically when `CRONWRAP_REQUIRE_ENV` is set.  No
changes to your crontab are needed.
