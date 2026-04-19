"""Tests for cronwrap.retry_budget_integration."""
from __future__ import annotations

import sys

import pytest

from cronwrap.retry_budget import RetryBudgetConfig
from cronwrap.retry_budget_integration import (
    check_budget_or_abort,
    run_with_retry_budget,
)
from cronwrap.runner import RunResult


def _ok() -> RunResult:
    return RunResult(command="echo hi", exit_code=0, stdout=b"hi", stderr=b"", duration=0.1)


def _fail() -> RunResult:
    return RunResult(command="false", exit_code=1, stdout=b"", stderr=b"err", duration=0.1)


class TestCheckBudgetOrAbort:
    def test_does_not_raise_when_budget_available(self, tmp_path):
        cfg = RetryBudgetConfig(max_retries=5, window_seconds=60, state_dir=str(tmp_path))
        check_budget_or_abort(cfg, "job1")  # should not raise

    def test_raises_system_exit_when_exhausted(self, tmp_path):
        cfg = RetryBudgetConfig(max_retries=1, window_seconds=60, state_dir=str(tmp_path))
        check_budget_or_abort(cfg, "job1")
        with pytest.raises(SystemExit):
            check_budget_or_abort(cfg, "job1")

    def test_disabled_skips_check(self, tmp_path):
        cfg = RetryBudgetConfig(max_retries=1, window_seconds=60,
                                state_dir=str(tmp_path), enabled=False)
        check_budget_or_abort(cfg, "job1")
        check_budget_or_abort(cfg, "job1")  # no error even though budget would be exceeded


class TestRunWithRetryBudget:
    def test_returns_success_immediately(self, tmp_path):
        cfg = RetryBudgetConfig(max_retries=5, window_seconds=60, state_dir=str(tmp_path))
        result, summary = run_with_retry_budget(cfg, "job", _ok, max_attempts=3)
        assert result.success
        assert "job" in summary

    def test_retries_on_failure(self, tmp_path):
        cfg = RetryBudgetConfig(max_retries=5, window_seconds=60, state_dir=str(tmp_path))
        calls = []

        def runner() -> RunResult:
            calls.append(1)
            if len(calls) < 3:
                return _fail()
            return _ok()

        result, _ = run_with_retry_budget(cfg, "job", runner, max_attempts=3)
        assert result.success
        assert len(calls) == 3

    def test_budget_exhausted_mid_retry_exits(self, tmp_path):
        cfg = RetryBudgetConfig(max_retries=1, window_seconds=60, state_dir=str(tmp_path))
        # first consume the budget
        from cronwrap.retry_budget import consume_retry
        consume_retry(cfg, "job")

        with pytest.raises(SystemExit):
            run_with_retry_budget(cfg, "job", _fail, max_attempts=3)
