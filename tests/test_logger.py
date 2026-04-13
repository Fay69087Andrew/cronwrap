"""Tests for cronwrap.logger module."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from cronwrap.logger import LogConfig, build_logger, log_result
from cronwrap.runner import RunResult


def _result(exit_code: int = 0, stderr: str = "") -> RunResult:
    return RunResult(
        command="echo hello",
        exit_code=exit_code,
        stdout="hello\n",
        stderr=stderr,
        duration_seconds=0.05,
    )


class TestLogConfig:
    def test_defaults(self):
        cfg = LogConfig()
        assert cfg.log_file is None
        assert cfg.log_level == "INFO"
        assert cfg.structured is False

    def test_log_level_uppercased(self):
        cfg = LogConfig(log_level="debug")
        assert cfg.log_level == "DEBUG"

    def test_invalid_log_level_raises(self):
        with pytest.raises(ValueError, match="Invalid log_level"):
            LogConfig(log_level="VERBOSE")

    def test_log_file_coerced_to_path(self):
        cfg = LogConfig(log_file="/tmp/cronwrap.log")
        assert isinstance(cfg.log_file, Path)


class TestBuildLogger:
    def test_returns_logger_instance(self):
        cfg = LogConfig()
        logger = build_logger(cfg, name="test_build")
        assert isinstance(logger, logging.Logger)

    def test_logger_level_applied(self):
        cfg = LogConfig(log_level="WARNING")
        logger = build_logger(cfg, name="test_level")
        assert logger.level == logging.WARNING

    def test_file_handler_created(self, tmp_path):
        log_file = tmp_path / "subdir" / "run.log"
        cfg = LogConfig(log_file=log_file)
        logger = build_logger(cfg, name="test_file")
        assert any(isinstance(h, logging.FileHandler) for h in logger.handlers)
        assert log_file.parent.exists()

    def test_stream_handler_when_no_file(self):
        cfg = LogConfig()
        logger = build_logger(cfg, name="test_stream")
        assert any(isinstance(h, logging.StreamHandler) for h in logger.handlers)


class TestLogResult:
    def test_plain_success_logs_info(self):
        cfg = LogConfig()
        logger = MagicMock()
        log_result(_result(exit_code=0), cfg, logger)
        logger.log.assert_called_once()
        level, message = logger.log.call_args[0]
        assert level == logging.INFO
        assert "SUCCESS" in message

    def test_plain_failure_logs_error(self):
        cfg = LogConfig()
        logger = MagicMock()
        log_result(_result(exit_code=1, stderr="oops"), cfg, logger)
        level, message = logger.log.call_args[0]
        assert level == logging.ERROR
        assert "FAILURE" in message
        assert "oops" in message

    def test_structured_output_is_valid_json(self):
        cfg = LogConfig(structured=True)
        logger = MagicMock()
        log_result(_result(exit_code=0), cfg, logger)
        _, message = logger.log.call_args[0]
        payload = json.loads(message)
        assert payload["success"] is True
        assert payload["exit_code"] == 0
        assert "timestamp" in payload

    def test_structured_failure_json(self):
        cfg = LogConfig(structured=True)
        logger = MagicMock()
        log_result(_result(exit_code=2, stderr="bad"), cfg, logger)
        level, message = logger.log.call_args[0]
        assert level == logging.ERROR
        payload = json.loads(message)
        assert payload["success"] is False
        assert payload["stderr"] == "bad"
