"""Tests for cronwrap.retry_budget."""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from cronwrap.retry_budget import (
    RetryBudgetConfig,
    RetryBudgetExceededError,
    RetryBudgetState,
    budget_summary,
    consume_retry,
    load_state,
    save_state,
)


class TestRetryBudgetConfig:
    def test_defaults(self):
        cfg = RetryBudgetConfig()
        assert cfg.max_retries == 10
        assert cfg.window_seconds == 3600
        assert cfg.enabled is True

    def test_zero_max_retries_raises(self):
        with pytest.raises(ValueError, match="max_retries"):
            RetryBudgetConfig(max_retries=0)

    def test_negative_max_retries_raises(self):
        with pytest.raises(ValueError):
            RetryBudgetConfig(max_retries=-1)

    def test_zero_window_raises(self):
        with pytest.raises(ValueError, match="window_seconds"):
            RetryBudgetConfig(window_seconds=0)

    def test_empty_state_dir_raises(self):
        with pytest.raises(ValueError, match="state_dir"):
            RetryBudgetConfig(state_dir="")

    def test_from_env_defaults(self, monkeypatch):
        for k in ("CRONWRAP_RETRY_BUDGET_MAX", "CRONWRAP_RETRY_BUDGET_WINDOW",
                  "CRONWRAP_RETRY_BUDGET_STATE_DIR", "CRONWRAP_RETRY_BUDGET_ENABLED"):
            monkeypatch.delenv(k, raising=False)
        cfg = RetryBudgetConfig.from_env()
        assert cfg.max_retries == 10
        assert cfg.enabled is True

    def test_from_env_custom(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_RETRY_BUDGET_MAX", "5")
        monkeypatch.setenv("CRONWRAP_RETRY_BUDGET_ENABLED", "false")
        cfg = RetryBudgetConfig.from_env()
        assert cfg.max_retries == 5
        assert cfg.enabled is False


class TestRetryBudgetState:
    def test_prune_removes_old(self):
        state = RetryBudgetState(attempts=[time.time() - 7200, time.time()])
        state.prune(3600)
        assert state.count() == 1

    def test_roundtrip(self):
        state = RetryBudgetState(attempts=[1.0, 2.0])
        assert RetryBudgetState.from_dict(state.to_dict()).attempts == [1.0, 2.0]


class TestConsumeRetry:
    def test_consumes_token(self, tmp_path):
        cfg = RetryBudgetConfig(max_retries=3, window_seconds=60, state_dir=str(tmp_path))
        state = consume_retry(cfg, "job1")
        assert state.count() == 1

    def test_raises_when_budget_exhausted(self, tmp_path):
        cfg = RetryBudgetConfig(max_retries=2, window_seconds=60, state_dir=str(tmp_path))
        consume_retry(cfg, "job1")
        consume_retry(cfg, "job1")
        with pytest.raises(RetryBudgetExceededError):
            consume_retry(cfg, "job1")

    def test_persists_state(self, tmp_path):
        cfg = RetryBudgetConfig(max_retries=5, window_seconds=60, state_dir=str(tmp_path))
        consume_retry(cfg, "myjob")
        state = load_state(cfg, "myjob")
        assert state.count() == 1


class TestBudgetSummary:
    def test_summary_contains_job(self, tmp_path):
        cfg = RetryBudgetConfig(max_retries=5, window_seconds=60, state_dir=str(tmp_path))
        summary = budget_summary(cfg, "myjob")
        assert "myjob" in summary
        assert "remaining=5" in summary
