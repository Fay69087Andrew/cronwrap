"""Tests for cronwrap.quota_integration."""
from __future__ import annotations

import sys
import time
from unittest.mock import MagicMock

import pytest

from cronwrap.quota import QuotaConfig, check_quota
from cronwrap.quota_integration import (
    build_quota_config,
    check_quota_or_abort,
    run_with_quota,
)
from cronwrap.runner import RunResult


def _ok() -> RunResult:
    return RunResult(command="echo hi", returncode=0, stdout=b"hi", stderr=b"")


class TestBuildQuotaConfig:
    def test_returns_quota_config(self):
        cfg = build_quota_config()
        assert isinstance(cfg, QuotaConfig)


class TestCheckQuotaOrAbort:
    def test_does_not_raise_when_quota_available(self, tmp_path):
        cfg = QuotaConfig(max_runs=5, window_seconds=60, state_dir=str(tmp_path))
        # Should not raise
        check_quota_or_abort(cfg, "job1")

    def test_raises_system_exit_when_exceeded(self, tmp_path):
        cfg = QuotaConfig(max_runs=1, window_seconds=60, state_dir=str(tmp_path))
        now = time.time()
        check_quota(cfg, "job2", now=now)
        with pytest.raises(SystemExit) as exc_info:
            check_quota_or_abort(cfg, "job2")
        assert exc_info.value.code == 1

    def test_calls_logger_on_exceeded(self, tmp_path):
        cfg = QuotaConfig(max_runs=1, window_seconds=60, state_dir=str(tmp_path))
        now = time.time()
        check_quota(cfg, "job3", now=now)
        logger = MagicMock()
        with pytest.raises(SystemExit):
            check_quota_or_abort(cfg, "job3", logger=logger)
        logger.assert_called_once()
        assert "job3" in logger.call_args[0][0]


class TestRunWithQuota:
    def test_returns_result_and_summary(self, tmp_path):
        cfg = QuotaConfig(max_runs=10, window_seconds=60, state_dir=str(tmp_path))
        result, summary = run_with_quota(cfg, "jobX", _ok)
        assert result.returncode == 0
        assert "quota:" in summary

    def test_aborts_when_quota_exceeded(self, tmp_path):
        cfg = QuotaConfig(max_runs=1, window_seconds=60, state_dir=str(tmp_path))
        now = time.time()
        check_quota(cfg, "jobY", now=now)
        with pytest.raises(SystemExit):
            run_with_quota(cfg, "jobY", _ok)

    def test_run_fn_called_once(self, tmp_path):
        cfg = QuotaConfig(max_runs=5, window_seconds=60, state_dir=str(tmp_path))
        fn = MagicMock(return_value=_ok())
        run_with_quota(cfg, "jobZ", fn)
        fn.assert_called_once()
