# Job Labeler

The `cronwrap.labeler` module lets you attach arbitrary key/value **labels** to
every job run. Labels are lightweight metadata — use them to slice dashboards,
filter history, or enrich alert emails.

## Quick start

```python
from cronwrap.labeler import LabelSet, from_env, label_summary

# Build manually
labels = LabelSet(labels={"env": "production", "team": "platform"})
print(labels.get("env"))        # production
print(label_summary(labels))   # labels: env=production, team=platform

# Merge two sets (right-hand side wins on conflicts)
overrides = LabelSet(labels={"env": "staging"})
merged = labels.merge(overrides)
print(merged.get("env"))       # staging
```

## Environment-variable driven

Set environment variables prefixed with `CRONWRAP_LABEL_` and call `from_env()`:

```bash
export CRONWRAP_LABEL_ENV=production
export CRONWRAP_LABEL_TEAM=platform
export CRONWRAP_LABEL_REGION=us-east-1
```

```python
labels = from_env()  # reads all CRONWRAP_LABEL_* vars
```

A custom prefix is supported:

```python
labels = from_env(prefix="JOB_LABEL_")
```

## Key / value rules

| Rule | Detail |
|------|--------|
| Key pattern | `[a-z][a-z0-9_.-]{0,62}` |
| Key max length | 63 characters |
| Value max length | 256 characters |
| Value type | Always stored as `str` |

Any violation raises a `ValueError` at construction time.

## API reference

### `LabelSet`

| Method | Description |
|--------|-------------|
| `get(key)` | Return value or `None` |
| `to_dict()` | Return a plain `dict` copy |
| `merge(other)` | Return new `LabelSet` with `other` overriding `self` |
| `__len__()` | Number of labels |

### `from_env(prefix)`

Reads all matching environment variables and returns a `LabelSet`.

### `label_summary(label_set)`

Returns a single human-readable string, e.g.:

```
labels: env=production, region=us-east-1, team=platform
```
