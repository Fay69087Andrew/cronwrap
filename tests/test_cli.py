"""Tests for cronwrap.cli module."""

import pytest
from unittest.mock import MagicMock, patch

from cronwrap.cli import build_parser, main
from cronwrap.runner import RunResult
from cronwrap.retry import RetryResult


def _make_run_result(returncode=0, stdout="ok", stderr=""):
    return RunResult(command=["echo", "ok"], returncode=returncode, stdout=stdout, stderr=stderr)


def _make_retry_result(returncode=0):
    result = _make_run_result(returncode=returncode)
    return RetryResult(attempts=[result])


class TestBuildParser:
    def test_parses_command(self):
        parser = build_parser()
        args = parser.parse_args(["echo", "hello"])
        assert "echo" in args.command

    def test_default_max_attempts(self):
        parser = build_parser()
        args = parser.parse_args(["echo"])
        assert args.max_attempts == 1

    def test_default_log_level(self):
        parser = build_parser()
        args = parser.parse_args(["echo"])
        assert args.log_level == "INFO"

    def test_alert_on_failure_flag(self):
        parser = build_parser()
        args = parser.parse_args(["--alert-on-failure", "echo"])
        assert args.alert_on_failure is True

    def test_job_name(self):
        parser = build_parser()
        args = parser.parse_args(["--job-name", "my-job", "echo"])
        assert args.job_name == "my-job"


class TestMain:
    @patch("cronwrap.cli.run_with_retry")
    @patch("cronwrap.cli.build_logger")
    @patch("cronwrap.cli.log_result")
    def test_returns_zero_on_success(self, mock_log, mock_build_logger, mock_retry):
        mock_retry.return_value = _make_retry_result(returncode=0)
        mock_build_logger.return_value = MagicMock()
        result = main(["echo", "hello"])
        assert result == 0

    @patch("cronwrap.cli.run_with_retry")
    @patch("cronwrap.cli.build_logger")
    @patch("cronwrap.cli.log_result")
    def test_returns_nonzero_on_failure(self, mock_log, mock_build_logger, mock_retry):
        mock_retry.return_value = _make_retry_result(returncode=1)
        mock_build_logger.return_value = MagicMock()
        result = main(["false"])
        assert result == 1

    @patch("cronwrap.cli.send_alert")
    @patch("cronwrap.cli.AlertConfig")
    @patch("cronwrap.cli.run_with_retry")
    @patch("cronwrap.cli.build_logger")
    @patch("cronwrap.cli.log_result")
    def test_alert_sent_on_failure(self, mock_log, mock_build_logger, mock_retry, mock_alert_cls, mock_send):
        mock_retry.return_value = _make_retry_result(returncode=1)
        mock_build_logger.return_value = MagicMock()
        mock_alert_cls.from_env.return_value = MagicMock()
        main(["--alert-on-failure", "false"])
        assert mock_send.called

    @patch("cronwrap.cli.send_alert")
    @patch("cronwrap.cli.run_with_retry")
    @patch("cronwrap.cli.build_logger")
    @patch("cronwrap.cli.log_result")
    def test_no_alert_on_success(self, mock_log, mock_build_logger, mock_retry, mock_send):
        mock_retry.return_value = _make_retry_result(returncode=0)
        mock_build_logger.return_value = MagicMock()
        main(["--alert-on-failure", "echo", "hi"])
        assert not mock_send.called
