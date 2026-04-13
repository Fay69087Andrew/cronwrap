"""Structured logging for cronwrap job runs."""

from __future__ import annotations

import json
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from cronwrap.runner import RunResult


@dataclass
class LogConfig:
    log_file: Optional[Path] = None
    log_level: str = "INFO"
    structured: bool = False

    def __post_init__(self) -> None:
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if self.log_level.upper() not in valid_levels:
            raise ValueError(
                f"Invalid log_level '{self.log_level}'. Must be one of {sorted(valid_levels)}."
            )
        self.log_level = self.log_level.upper()
        if self.log_file is not None:
            self.log_file = Path(self.log_file)


def build_logger(config: LogConfig, name: str = "cronwrap") -> logging.Logger:
    """Build and return a configured logger instance.

    Args:
        config: A LogConfig instance controlling log level, destination, and format.
        name: The logger name; defaults to 'cronwrap'.

    Returns:
        A fully configured :class:`logging.Logger`.
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, config.log_level))
    logger.handlers.clear()

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    if config.log_file:
        config.log_file.parent.mkdir(parents=True, exist_ok=True)
        handler: logging.Handler = logging.FileHandler(config.log_file)
    else:
        handler = logging.StreamHandler(sys.stdout)

    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


def log_result(result: RunResult, config: LogConfig, logger: logging.Logger) -> None:
    """Log a RunResult using either structured JSON or plain text format.

    Args:
        result: The RunResult produced by executing a cron job command.
        config: A LogConfig instance controlling the output format.
        logger: The logger to emit the message on.
    """
    timestamp = datetime.now(timezone.utc).isoformat()

    if config.structured:
        payload = {
            "timestamp": timestamp,
            "command": result.command,
            "exit_code": result.exit_code,
            "success": result.success,
            "duration_seconds": result.duration_seconds,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
        message = json.dumps(payload)
    else:
        status = "SUCCESS" if result.success else "FAILURE"
        message = (
            f"[{status}] command={result.command!r} "
            f"exit_code={result.exit_code} "
            f"duration={result.duration_seconds:.3f}s"
        )
        if result.stderr:
            message += f" stderr={result.stderr.strip()!r}"

    level = logging.INFO if result.success else logging.ERROR
    logger.log(level, message)
