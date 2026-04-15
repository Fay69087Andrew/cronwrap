# Signal Handler

The `cronwrap.signal_handler` module provides graceful OS signal handling so
that a running cron job can respond to `SIGTERM` / `SIGINT` without leaving
orphaned child processes or corrupted state.

## Configuration

| Environment variable | Default | Description |
|---|---|---|
| `CRONWRAP_HANDLE_SIGTERM` | `true` | Intercept `SIGTERM` |
| `CRONWRAP_HANDLE_SIGINT` | `true` | Intercept `SIGINT` |
| `CRONWRAP_SIGNAL_PROPAGATE` | `true` | Forward signal to the child PID |

## Usage

```python
from cronwrap.signal_handler import (
    SignalHandlerConfig,
    SignalState,
    register_handlers,
    signal_summary,
)

cfg = SignalHandlerConfig.from_env()
state = SignalState()

# Register before launching the child process
register_handlers(cfg, state, child_pid=child.pid)

# … run the job …

if state.terminated:
    print("Job was interrupted by signal", state.received)

print(signal_summary(state))
```

## `SignalHandlerConfig`

```python
@dataclass
class SignalHandlerConfig:
    handle_sigterm: bool = True
    handle_sigint: bool  = True
    propagate_to_child: bool = True
```

## `SignalState`

A lightweight mutable container updated by the installed handler.

| Attribute | Type | Description |
|---|---|---|
| `received` | `int \| None` | Signal number, or `None` if no signal received |
| `terminated` | `bool` | `True` when any signal has been received |

## `register_handlers(config, state, child_pid, extra_callback)`

Installs handlers for the configured signals.  When a signal fires:

1. `state.received` is set to the signal number.
2. If `propagate_to_child` is `True` and `child_pid` is provided, the signal
   is forwarded with `os.kill`.
3. `extra_callback(signum)` is called if supplied.

## `signal_summary(state) -> dict`

Returns a plain dictionary suitable for structured logging:

```python
{"terminated": True, "signal": 15}
```
