# cronwrap

A CLI wrapper around cron jobs that adds logging, failure alerts, and retry logic without touching crontab syntax.

---

## Installation

```bash
pip install cronwrap
```

Or install from source:

```bash
git clone https://github.com/yourname/cronwrap.git && cd cronwrap && pip install .
```

---

## Usage

Wrap any existing cron command with `cronwrap` to get instant logging, alerting, and retries:

```bash
cronwrap --retries 3 --alert email@example.com -- /path/to/your/script.sh
```

Then in your crontab (`crontab -e`), simply prefix your command:

```
*/15 * * * * cronwrap --retries 2 --log /var/log/myjob.log -- python /opt/jobs/sync.py
```

### Options

| Flag | Description |
|------|-------------|
| `--retries N` | Retry the command up to N times on failure |
| `--log FILE` | Write stdout/stderr to the specified log file |
| `--alert EMAIL` | Send an email alert if the command ultimately fails |
| `--timeout SEC` | Kill the command if it runs longer than SEC seconds |

---

## How It Works

1. **Executes** your command as a subprocess
2. **Logs** all output with timestamps to a file or stdout
3. **Retries** on non-zero exit codes up to the specified limit
4. **Alerts** via email if all retries are exhausted

---

## License

MIT © 2024 [Your Name](https://github.com/yourname)