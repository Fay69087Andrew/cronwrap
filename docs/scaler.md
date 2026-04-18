# Dynamic Scaler

The `cronwrap.scaler` module provides a lightweight recommendation engine that
suggests how many concurrent instances of a job should run, based on recent
execution durations.

## Overview

The scaler does **not** manage processes directly — it analyses a sliding window
of past durations and returns a `ScaleDecision` that your orchestration layer
can act on.

## Configuration

| Env var | Default | Description |
|---|---|---|
| `CRONWRAP_SCALER_ENABLED` | `true` | Enable/disable the scaler |
| `CRONWRAP_SCALER_MIN` | `1` | Minimum recommended instances |
| `CRONWRAP_SCALER_MAX` | `4` | Maximum recommended instances |
| `CRONWRAP_SCALER_TARGET` | `60` | Target duration in seconds |
| `CRONWRAP_SCALER_UP_THRESHOLD` | `1.5` | Scale up when avg/target ≥ this |
| `CRONWRAP_SCALER_DOWN_THRESHOLD` | `0.5` | Scale down when avg/target ≤ this |
| `CRONWRAP_SCALER_WINDOW` | `5` | Number of recent runs to average |

## Usage

```python
from cronwrap.scaler import ScalerConfig, evaluate_scale, scaler_summary

cfg = ScalerConfig.from_env()
durations = [55.0, 62.0, 98.0, 105.0]  # seconds per recent run
decision = evaluate_scale(cfg, durations, current_instances=2)
print(scaler_summary(decision))
# scaler: scale-up | avg=80.0s current=2 recommended=3
```

## Scale decisions

- **scale-up** — average duration ÷ target ≥ `scale_up_threshold`
- **scale-down** — average duration ÷ target ≤ `scale_down_threshold`
- **stable** — ratio is within thresholds; no change recommended
- **no-op** — scaler is disabled or no duration history is available

## Notes

- Only the most recent `window` durations are considered.
- Recommendations are clamped to `[min_instances, max_instances]`.
- The scaler is stateless; persist durations externally (e.g. via `HistoryStore`).
