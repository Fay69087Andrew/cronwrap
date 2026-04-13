"""CLI entry point for cronwrap."""

import argparse
import os
import sys
from typing import Optional

from cronwrap.alerts import AlertConfig, send_alert
from cronwrap.logger import LogConfig, build_logger, log_result
from cronwrap.retry import RetryConfig, run_with_retry
from cronwrap.runner import run_command


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap",
        description="Wrap cron jobs with logging, alerts, and retry logic.",
    )
    parser.add_argument("command", nargs=argparse.REMAINDER, help="Command to run")
    parser.add_argument("--max-attempts", type=int, default=1, help="Max retry attempts")
    parser.add_argument("--delay", type=float, default=0.0, help="Delay between retries (seconds)")
    parser.add_argument("--log-file", default=None, help="Path to log file")
    parser.add_argument("--log-level", default="INFO", help="Log level (default: INFO)")
    parser.add_argument("--alert-on-failure", action="store_true", help="Send email alert on failure")
    parser.add_argument("--job-name", default=None, help="Human-readable job name for alerts/logs")
    return parser


def main(argv: Optional[list] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    command = [c for c in (args.command or []) if c != "--"]
    if not command:
        parser.error("No command provided.")

    job_name = args.job_name or " ".join(command)

    log_config = LogConfig(
        log_file=args.log_file,
        log_level=args.log_level.upper(),
    )
    logger = build_logger(log_config, job_name)

    retry_config = RetryConfig(
        max_attempts=args.max_attempts,
        delay=args.delay,
    )

    retry_result = run_with_retry(command, retry_config)
    final = retry_result.final()

    log_result(logger, final, job_name)

    if args.alert_on_failure and not retry_result.succeeded():
        alert_config = AlertConfig.from_env()
        send_alert(alert_config, final, job_name)

    return final.returncode if final.returncode is not None else 1


if __name__ == "__main__":
    sys.exit(main())
