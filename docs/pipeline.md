# Pipeline

The `pipeline` module lets you chain multiple shell commands as sequential steps,
with optional stop-on-failure control and a structured result.

## Configuration

| Env var | Default | Description |
|---|---|---|
| `CRONWRAP_PIPELINE_STEPS` | `` | Semicolon-separated list of commands |
| `CRONWRAP_PIPELINE_STOP_ON_FAILURE` | `true` | Stop executing steps after first failure |
| `CRONWRAP_PIPELINE_LABEL` | `pipeline` | Human-readable label for the pipeline |

## Usage

```python
from cronwrap.pipeline import PipelineConfig
from cronwrap.pipeline_integration import run_pipeline, pipeline_summary

cfg = PipelineConfig(
    steps=["./scripts/backup.sh", "./scripts/upload.sh", "./scripts/notify.sh"],
    stop_on_failure=True,
    label="nightly-backup",
)

result = run_pipeline(cfg)
print(pipeline_summary(result))

if not result.succeeded:
    raise SystemExit(1)
```

## PipelineResult

- `succeeded` — `True` if all executed steps returned exit code 0
- `total_steps` — number of steps that were executed
- `passed_steps` — number of steps that succeeded
- `aborted_at` — index of the step that caused an abort (or `None`)
- `step_results` — list of `StepResult` objects

## StepResult

Each `StepResult` exposes:
- `index`, `command`, `exit_code`, `stdout`, `stderr`
- `succeeded` property

## From environment

```bash
export CRONWRAP_PIPELINE_STEPS="./step1.sh;./step2.sh;./step3.sh"
export CRONWRAP_PIPELINE_STOP_ON_FAILURE=true
export CRONWRAP_PIPELINE_LABEL=deploy
```

Then call `PipelineConfig.from_env()` or `build_pipeline_config()`.
