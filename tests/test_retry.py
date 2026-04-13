"""Tests for cronwrap.retry."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from cronwrap.retry import RetryConfig, RetryResult, run_with_retry
from cronwrap.runner import RunResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _result(exit_code: int) -> RunResult:
    return RunResult(command="echo hi", exit_code=exit_code, stdout="", stderr="")


# ---------------------------------------------------------------------------
# RetryConfig
# ---------------------------------------------------------------------------

class TestRetryConfig:
    def test_defaults(self):
        cfg = RetryConfig()
        assert cfg.max_attempts == 1
        assert cfg.delay_seconds == 0.0
        assert cfg.backoff_factor == 1.0

    def test_invalid_max_attempts(self):
        with pytest.raises(ValueError, match="max_attempts"):
            RetryConfig(max_attempts=0)

    def test_invalid_delay(self):
        with pytest.raises(ValueError, match="delay_seconds"):
            RetryConfig(delay_seconds=-1)

    def test_invalid_backoff(self):
        with pytest.raises(ValueError, match="backoff_factor"):
            RetryConfig(backoff_factor=0.5)


# ---------------------------------------------------------------------------
# RetryResult
# ---------------------------------------------------------------------------

class TestRetryResult:
    def test_final_returns_last(self):
        rr = RetryResult(attempts=[_result(1), _result(0)])
        assert rr.final.exit_code == 0

    def test_succeeded_true_when_final_zero(self):
        rr = RetryResult(attempts=[_result(1), _result(0)])
        assert rr.succeeded is True

    def test_succeeded_false_when_final_nonzero(self):
        rr = RetryResult(attempts=[_result(1), _result(2)])
        assert rr.succeeded is False

    def test_total_attempts(self):
        rr = RetryResult(attempts=[_result(1), _result(1), _result(0)])
        assert rr.total_attempts == 3

    def test_str_contains_status_and_attempts(self):
        rr = RetryResult(attempts=[_result(0)])
        s = str(rr)
        assert "succeeded" in s
        assert "attempts=1" in s


# ---------------------------------------------------------------------------
# run_with_retry
# ---------------------------------------------------------------------------

class TestRunWithRetry:
    def test_success_on_first_attempt(self):
        with patch("cronwrap.retry.run_command", return_value=_result(0)) as mock_run:
            result = run_with_retry("echo hi")
        assert result.succeeded
        assert result.total_attempts == 1
        mock_run.assert_called_once()

    def test_retries_on_failure_then_succeeds(self):
        side_effects = [_result(1), _result(0)]
        sleep_mock = MagicMock()
        with patch("cronwrap.retry.run_command", side_effect=side_effects):
            result = run_with_retry(
                "cmd",
                RetryConfig(max_attempts=3, delay_seconds=1.0),
                _sleep=sleep_mock,
            )
        assert result.succeeded
        assert result.total_attempts == 2
        sleep_mock.assert_called_once_with(1.0)

    def test_exhausts_all_attempts_on_persistent_failure(self):
        sleep_mock = MagicMock()
        with patch("cronwrap.retry.run_command", return_value=_result(1)):
            result = run_with_retry(
                "bad_cmd",
                RetryConfig(max_attempts=3),
                _sleep=sleep_mock,
            )
        assert not result.succeeded
        assert result.total_attempts == 3

    def test_backoff_increases_delay(self):
        sleep_calls: list[float] = []
        with patch("cronwrap.retry.run_command", return_value=_result(1)):
            run_with_retry(
                "cmd",
                RetryConfig(max_attempts=4, delay_seconds=1.0, backoff_factor=2.0),
                _sleep=lambda s: sleep_calls.append(s),
            )
        assert sleep_calls == [1.0, 2.0, 4.0]

    def test_no_sleep_when_delay_is_zero(self):
        sleep_mock = MagicMock()
        with patch("cronwrap.retry.run_command", return_value=_result(1)):
            run_with_retry(
                "cmd",
                RetryConfig(max_attempts=2, delay_seconds=0.0),
                _sleep=sleep_mock,
            )
        sleep_mock.assert_not_called()

    def test_default_config_used_when_none_given(self):
        with patch("cronwrap.retry.run_command", return_value=_result(0)) as mock_run:
            result = run_with_retry("echo")
        assert result.total_attempts == 1
        mock_run.assert_called_once_with("echo")
