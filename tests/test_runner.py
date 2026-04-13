"""Tests for cronwrap.runner module."""

import pytest
from unittest.mock import patch
import time

from cronwrap.runner import run_command, RunResult


class TestRunResult:
    def test_success_property_true_on_zero_exit(self):
        result = RunResult(
            command="echo hi",
            exit_code=0,
            stdout="hi\n",
            stderr="",
            duration_seconds=0.1,
            started_at=time.time(),
        )
        assert result.success is True

    def test_success_property_false_on_nonzero_exit(self):
        result = RunResult(
            command="false",
            exit_code=1,
            stdout="",
            stderr="",
            duration_seconds=0.05,
            started_at=time.time(),
        )
        assert result.success is False

    def test_str_includes_status_and_command(self):
        result = RunResult(
            command="echo hello",
            exit_code=0,
            stdout="hello\n",
            stderr="",
            duration_seconds=0.02,
            started_at=time.time(),
        )
        assert "SUCCESS" in str(result)
        assert "echo hello" in str(result)


class TestRunCommand:
    def test_successful_command(self):
        result = run_command("echo hello")
        assert result.success
        assert "hello" in result.stdout
        assert result.exit_code == 0
        assert result.attempts == 1

    def test_failing_command(self):
        result = run_command("exit 1")
        assert not result.success
        assert result.exit_code == 1

    def test_stderr_captured(self):
        result = run_command("echo error_msg >&2")
        assert "error_msg" in result.stderr

    def test_retries_on_failure(self):
        result = run_command("exit 1", retries=2, retry_delay=0.01)
        assert result.attempts == 3
        assert not result.success

    def test_no_retry_on_success(self):
        result = run_command("echo ok", retries=3, retry_delay=0.01)
        assert result.attempts == 1
        assert result.success

    def test_timeout_returns_error_result(self):
        result = run_command("sleep 10", timeout=1)
        assert not result.success
        assert result.exit_code == -1
        assert result.error is not None
        assert "Timeout" in result.error

    def test_duration_is_positive(self):
        result = run_command("echo fast")
        assert result.duration_seconds > 0

    def test_command_stored_in_result(self):
        cmd = "echo stored"
        result = run_command(cmd)
        assert result.command == cmd
