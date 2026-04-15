# Profiler

The `profiler` module measures wall-clock execution time for cron jobs and
classifies the result as **ok**, **warn**, or **critical** based on configurable
thresholds.

## Configuration

| Environment variable | Default | Description |
|---|---|---|
| `CRONWRAP_PROFILER_ENABLED` | `true` | Set to `false` to disable profiling |
| `CRONWRAP_PROFILER_WARN_SECONDS` | `60` | Elapsed seconds before a `warn` level is emitted |
| `CRONWRAP_PROFILER_CRITICAL_SECONDS` | `300` | Elapsed seconds before a `critical` level is emitted |

## Programmatic usage

```python
from cronwrap.profiler import Profiler, ProfilerConfig

cfg = ProfilerConfig(warn_threshold_seconds=30, critical_threshold_seconds=120)

with Profiler(cfg, label="nightly-report") as p:
    run_my_job()

print(p.result.summary())
# elapsed=45.123s level=warn (warn>=30s critical>=120s)
```

## Integration helper

```python
from cronwrap.profiler_integration import run_with_profiler, build_profiler_config

cfg = build_profiler_config()  # reads from os.environ
result, profile = run_with_profiler(lambda: run_command("./my_script.sh"), cfg)

if profile.level != "ok":
    print(f"WARNING: {profile.summary()}")
```

## Levels

| Level | Condition |
|---|---|
| `ok` | `elapsed < warn_threshold_seconds` |
| `warn` | `warn_threshold_seconds <= elapsed < critical_threshold_seconds` |
| `critical` | `elapsed >= critical_threshold_seconds` |
