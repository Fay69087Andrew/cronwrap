# Job Tags

Cronwrap lets you attach arbitrary **key/value tags** to every job run.  Tags
are propagated to log entries, audit records, and webhook payloads so you can
filter and group runs in downstream systems.

---

## Defining tags

### Via environment variables

Any environment variable whose name starts with `CRONWRAP_TAG_` is
automatically collected.  The tag key is the lower-cased suffix.

```bash
export CRONWRAP_TAG_ENV=production
export CRONWRAP_TAG_TEAM=platform
export CRONWRAP_TAG_SERVICE=billing-worker

cronwrap -- python billing.py
```

This produces the tag set `{"env": "production", "team": "platform", "service": "billing-worker"}`.

### Via the CLI flag

Pass `--tags` with a comma-separated list of `key=value` pairs:

```bash
cronwrap --tags env=prod,region=eu -- python billing.py
```

CLI tags are **merged** with environment tags; CLI values take precedence.

---

## Tag rules

| Constraint | Limit |
|------------|-------|
| Key characters | `[a-zA-Z0-9_-]` |
| Key length | 1 – 64 characters |
| Value length | ≤ 256 characters |
| Value type | Always stored as a string |

Violating any constraint raises a `ValueError` at startup so misconfigured
jobs fail fast rather than silently dropping tags.

---

## Python API

```python
from cronwrap.tags import TagSet, from_env, parse_tags

# Build from env
ts = from_env()                        # reads CRONWRAP_TAG_* vars

# Build from a string (e.g. CLI argument)
ts = parse_tags("env=prod,team=ops")

# Merge two sets (right-hand side wins on conflict)
combined = from_env().merge(parse_tags("env=staging"))

print(combined.get("env"))   # "staging"
print(combined.to_dict())    # {'env': 'staging', 'team': 'ops', ...}
```

---

## Integration with other modules

- **Audit** — `AuditEntry` stores a `tags` dict alongside each run record.
- **Webhook** — `send_webhook` includes `tags` in the JSON payload.
- **Metrics** — `JobMetric` carries tags so time-series backends can slice by label.
