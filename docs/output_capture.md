# Output Capture

`cronwrap` can capture, decode, and optionally truncate the stdout and stderr
produced by a cron job before passing it to the logger, alerter, or webhook.

## Configuration

All settings can be provided via environment variables or by constructing an
`OutputCaptureConfig` directly in Python.

| Environment variable | Default | Description |
|---|---|---|
| `CRONWRAP_MAX_OUTPUT_BYTES` | `1048576` (1 MiB) | Maximum bytes captured across stdout + stderr. Output beyond this limit is silently dropped and `truncated` is set to `True`. |
| `CRONWRAP_OUTPUT_ENCODING` | `utf-8` | Codec used to decode raw bytes. Invalid byte sequences are replaced with the Unicode replacement character. |
| `CRONWRAP_CAPTURE_STDOUT` | `true` | Set to `false` to discard stdout entirely. |
| `CRONWRAP_CAPTURE_STDERR` | `true` | Set to `false` to discard stderr entirely. |

## Quick start

```python
from cronwrap.output_capture import OutputCaptureConfig, decode_output

cfg = OutputCaptureConfig.from_env()
result = decode_output(raw_stdout=b"ok", raw_stderr=b"", config=cfg)
print(result.stdout)    # "ok"
print(result.truncated) # False
```

## Truncation

When the combined size of stdout and stderr exceeds `max_bytes`, the
`CapturedOutput.truncated` flag is set to `True`.  Stdout bytes are taken
first; any remaining budget is used for stderr.

```bash
export CRONWRAP_MAX_OUTPUT_BYTES=512
```

## Combining streams

Use `CapturedOutput.combined()` to get a single string with stdout and stderr
separated by a newline (empty streams are omitted):

```python
print(result.combined())
```

## Integration with the runner

The runner automatically passes raw subprocess bytes through `decode_output`
using the active `OutputCaptureConfig` so that all downstream components
(logger, alerts, webhooks) receive clean, bounded strings.
