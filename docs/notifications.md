# Notifications

`cronwrap` can dispatch alert notifications when a job fails (or on every run).
Notifications are controlled via environment variables or the `NotifierConfig` dataclass.

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `CRONWRAP_NOTIFY_ENABLED` | `true` | Set to `false` to disable all notifications. |
| `CRONWRAP_NOTIFY_ECHO` | `false` | Set to `true` to print the alert to stdout even when no SMTP is configured. |
| `CRONWRAP_NOTIFY_FAILURE_ONLY` | `true` | Set to `false` to notify on every run, including successes. |
| `CRONWRAP_SMTP_HOST` | *(none)* | SMTP server hostname. Required for email alerts. |
| `CRONWRAP_SMTP_PORT` | `587` | SMTP server port. |
| `CRONWRAP_ALERT_TO` | *(none)* | Recipient email address. |
| `CRONWRAP_ALERT_FROM` | `cronwrap@localhost` | Sender email address. |

## How It Works

1. After a job completes (including any retries), `notify()` is called with the
   final `RunResult` and the `RetryResult`.
2. If `failure_only=True` (the default) and the job succeeded, no notification
   is sent.
3. If SMTP is configured (`CRONWRAP_SMTP_HOST` + `CRONWRAP_ALERT_TO`), an email
   is dispatched via `send_alert()`.
4. If `echo=True`, the alert subject and body are printed to stdout regardless
   of SMTP configuration — useful for debugging or pipe-based alerting.

## Example

```bash
export CRONWRAP_SMTP_HOST=smtp.example.com
export CRONWRAP_ALERT_TO=ops@example.com
export CRONWRAP_NOTIFY_ECHO=true

cronwrap --max-attempts 3 -- /usr/local/bin/my-job.sh
```

On failure, an email is sent **and** the alert is printed to stdout.
