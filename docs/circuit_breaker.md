# Circuit Breaker

The circuit breaker prevents cronwrap from repeatedly running a job that is
consistently failing, giving downstream services time to recover.

## How it works

| State | Meaning |
|-------|---------|
| `closed` | Normal operation — job runs as scheduled. |
| `open` | Job is skipped; too many consecutive failures detected. |
| `half-open` | Recovery timeout elapsed; next run is allowed as a probe. |

## Configuration

Set these environment variables to control the circuit breaker:

| Variable | Default | Description |
|----------|---------|-------------|
| `CRONWRAP_CB_ENABLED` | `false` | Enable the circuit breaker. |
| `CRONWRAP_CB_FAILURE_THRESHOLD` | `3` | Consecutive failures before opening. |
| `CRONWRAP_CB_RECOVERY_TIMEOUT` | `300` | Seconds before moving to half-open. |
| `CRONWRAP_CB_STATE_DIR` | `/tmp/cronwrap/circuit` | Directory for per-job state files. |

## Example

```bash
export CRONWRAP_CB_ENABLED=true
export CRONWRAP_CB_FAILURE_THRESHOLD=3
export CRONWRAP_CB_RECOVERY_TIMEOUT=120

cronwrap --job-name nightly-report -- python report.py
```

After 3 consecutive non-zero exits cronwrap will print:

```
[cronwrap] Circuit breaker OPEN for job 'nightly-report' after 3 consecutive
failure(s). Skipping execution.
```

and exit without running the command. After 120 seconds the circuit moves to
`half-open` and the next scheduled invocation is allowed through as a probe.
A successful probe closes the circuit; a failed probe re-opens it.

## State files

Each job stores its circuit state in a small JSON file:

```
/tmp/cronwrap/circuit/<job-name>.json
```

You can inspect or reset the circuit manually:

```bash
# inspect
cat /tmp/cronwrap/circuit/nightly-report.json

# reset (close the circuit)
rm /tmp/cronwrap/circuit/nightly-report.json
```
