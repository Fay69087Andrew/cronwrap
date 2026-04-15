"""Tests for cronwrap.budget_integration."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from cronwrap.budget import BudgetConfig, record_budget
from cronwrap.budget_integration import (
    build_budget_config,
    budget_summary,
    check_budget_or_abort,
    run_with_budget,
)
from cronwrap.runner import RunResult


def _ok() -> RunResult:
    r = MagicMock(spec=RunResult)
    r.exit_code = 0
    return r


def _cfg(tmp_path, max_seconds=3600.0, enabled=True) -> BudgetConfig:
    return BudgetConfig(
        max_seconds=max_seconds,
        window_seconds=86400.0,
        state_dir=str(tmp_path),
        enabled=enabled,
    )


class TestCheckBudgetOrAbort:
    def test_does_not_raise_when_ok(self, tmp_path):
        check_budget_or_abort(_cfg(tmp_path), "job", now=1000.0)

    def test_raises_system_exit_when_exhausted(self, tmp_path):
        cfg = _cfg(tmp_path, max_seconds=5.0)
        record_budget(cfg, "job", 10.0, now=1000.0)
        with pytest.raises(SystemExit, match="Budget exhausted"):
            check_budget_or_abort(cfg, "job", now=1500.0)

    def test_skips_check_when_disabled(self, tmp_path):
        cfg = _cfg(tmp_path, max_seconds=1.0, enabled=False)
        record_budget(BudgetConfig(max_seconds=1.0, window_seconds=86400.0, state_dir=str(tmp_path)), "job", 999.0, now=1.0)
        # should not raise even though budget would be exceeded
        check_budget_or_abort(cfg, "job", now=500.0)


class TestRunWithBudget:
    def test_returns_result_and_summary(self, tmp_path):
        cfg = _cfg(tmp_path)
        result, summary = run_with_budget(cfg, "job", _ok, now=1000.0)
        assert result.exit_code == 0
        assert "job" in summary

    def test_records_duration(self, tmp_path):
        cfg = _cfg(tmp_path)
        run_with_budget(cfg, "job", _ok, now=1000.0)
        from cronwrap.budget import load_budget_state
        state = load_budget_state(cfg, "job")
        assert state.total_seconds() >= 0.0
        assert len(state.runs) == 1

    def test_aborts_when_budget_exceeded(self, tmp_path):
        cfg = _cfg(tmp_path, max_seconds=1.0)
        record_budget(cfg, "job", 5.0, now=100.0)
        with pytest.raises(SystemExit):
            run_with_budget(cfg, "job", _ok, now=200.0)


class TestBudgetSummary:
    def test_contains_job_name(self, tmp_path):
        cfg = _cfg(tmp_path)
        summary = budget_summary(cfg, "myjob", last_duration=12.3)
        assert "myjob" in summary
        assert "12.3" in summary

    def test_disabled_message(self, tmp_path):
        cfg = _cfg(tmp_path, enabled=False)
        summary = budget_summary(cfg, "myjob", last_duration=0.0)
        assert "disabled" in summary


def test_build_budget_config(monkeypatch):
    monkeypatch.delenv("CRONWRAP_BUDGET_MAX_SECONDS", raising=False)
    cfg = build_budget_config()
    assert isinstance(cfg, BudgetConfig)
