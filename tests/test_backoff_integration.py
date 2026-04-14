"""Tests for cronwrap.backoff_integration."""
from __future__ import annotations

from unittest.mock import MagicMock, call, patch

import pytest

from cronwrap.backoff import BackoffConfig
from cronwrap.backoff_integration import backoff_summary, run_with_backoff
from cronwrap.runner import RunResult


def _result(exit_code: int) -> RunResult:
    return RunResult(command="echo test", exit_code=exit_code, stdout=b"", stderr=b"")


class TestRunWithBackoff:
    def test_succeeds_on_first_attempt(self):
        run_fn = MagicMock(return_value=_result(0))
        sleep = MagicMock()
        cfg = BackoffConfig(jitter=False)
        result, attempts = run_with_backoff(run_fn, max_attempts=3, config=cfg, _sleep=sleep)
        assert result.success
        assert attempts == 1
        sleep.assert_not_called()

    def test_retries_on_failure_then_succeeds(self):
        responses = [_result(1), _result(1), _result(0)]
        run_fn = MagicMock(side_effect=responses)
        sleep = MagicMock()
        cfg = BackoffConfig(base=2.0, jitter=False)
        result, attempts = run_with_backoff(run_fn, max_attempts=3, config=cfg, _sleep=sleep)
        assert result.success
        assert attempts == 3
        assert sleep.call_count == 2

    def test_exhausts_all_attempts_on_persistent_failure(self):
        run_fn = MagicMock(return_value=_result(1))
        sleep = MagicMock()
        cfg = BackoffConfig(jitter=False)
        result, attempts = run_with_backoff(run_fn, max_attempts=4, config=cfg, _sleep=sleep)
        assert not result.success
        assert attempts == 4
        assert sleep.call_count == 3  # no sleep after last attempt

    def test_no_sleep_after_final_attempt(self):
        run_fn = MagicMock(return_value=_result(2))
        sleep = MagicMock()
        cfg = BackoffConfig(jitter=False)
        run_with_backoff(run_fn, max_attempts=2, config=cfg, _sleep=sleep)
        assert sleep.call_count == 1

    def test_invalid_max_attempts_raises(self):
        with pytest.raises(ValueError, match="max_attempts"):
            run_with_backoff(lambda: _result(0), max_attempts=0)

    def test_uses_default_config_when_none_provided(self):
        run_fn = MagicMock(return_value=_result(0))
        result, attempts = run_with_backoff(run_fn, max_attempts=1, _sleep=MagicMock())
        assert result.success

    def test_sleep_duration_grows_with_attempt(self):
        responses = [_result(1), _result(1), _result(0)]
        run_fn = MagicMock(side_effect=responses)
        sleep = MagicMock()
        cfg = BackoffConfig(base=2.0, jitter=False)
        run_with_backoff(run_fn, max_attempts=3, config=cfg, _sleep=sleep)
        delays = [c.args[0] for c in sleep.call_args_list]
        assert delays[1] > delays[0]


class TestBackoffSummary:
    def test_success_message(self):
        r = _result(0)
        msg = backoff_summary(r, attempts=2, max_attempts=5)
        assert "succeeded" in msg
        assert "2/5" in msg
        assert "exit_code=0" in msg

    def test_failure_message(self):
        r = _result(1)
        msg = backoff_summary(r, attempts=5, max_attempts=5)
        assert "failed" in msg
        assert "5/5" in msg
        assert "exit_code=1" in msg
