"""cronwrap — A CLI wrapper around cron jobs.

Provides logging, failure alerts, and retry logic
without touching crontab syntax.
"""

__version__ = "0.1.0"
__author__ = "cronwrap contributors"

from cronwrap.runner import run_command, RunResult

__all__ = ["run_command", "RunResult"]
