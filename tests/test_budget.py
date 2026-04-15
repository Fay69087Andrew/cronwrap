"""Tests for cronwrap.budget."""
from __future__ import annotations

import json
import pytest
from pathlib import Path
from unittest.mock import patch

from cronwrap.budget import (
    BudgetConfig,
    BudgetExceededError,
    BudgetState,
    check_budget,
    load_budget_state,
    record_budget,
    save_budget_state,
)


# ---------------------------------------------------------------------------
# BudgetConfig
# ---------------------------------------------------------------------------

class TestBudgetConfig:
    def test_defaults(self):
        cfg = BudgetConfig()
        assert cfg.max_seconds == 3600.0
        assert cfg.window_seconds == 86400.0
        assert cfg.enabled is True

    def test_zero_max_seconds_raises(self):
        with pytest.raises(ValueError, match="max_seconds"):
            BudgetConfig(max_seconds=0)

    def test_negative_max_seconds_raises(self):
        with pytest.raises(ValueError, match="max_seconds"):
            BudgetConfig(max_seconds=-1)

    def test_zero_window_raises(self):
        with pytest.raises(ValueError, match="window_seconds"):
            BudgetConfig(window_seconds=0)

    def test_empty_state_dir_raises(self):
        with pytest.raises(ValueError, match="state_dir"):
            BudgetConfig(state_dir="")

    def test_from_env_defaults(self, monkeypatch):
        for k in ("CRONWRAP_BUDGET_MAX_SECONDS", "CRONWRAP_BUDGET_WINDOW_SECONDS",
                  "CRONWRAP_BUDGET_STATE_DIR", "CRONWRAP_BUDGET_ENABLED"):
            monkeypatch.delenv(k, raising=False)
        cfg = BudgetConfig.from_env()
        assert cfg.max_seconds == 3600.0
        assert cfg.enabled is True

    def test_from_env_custom(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_BUDGET_MAX_SECONDS", "600")
        monkeypatch.setenv("CRONWRAP_BUDGET_ENABLED", "false")
        cfg = BudgetConfig.from_env()
        assert cfg.max_seconds == 600.0
        assert cfg.enabled is False


# ---------------------------------------------------------------------------
# BudgetState
# ---------------------------------------------------------------------------

class TestBudgetState:
    def test_empty_total(self):
        assert BudgetState().total_seconds() == 0.0

    def test_record_accumulates(self):
        s = BudgetState()
        s.record(10.0, now=1000.0)
        s.record(5.0, now=1010.0)
        assert s.total_seconds() == 15.0

    def test_prune_removes_old(self):
        s = BudgetState()
        s.record(100.0, now=0.0)
        s.record(50.0, now=500.0)
        s.prune(window_seconds=200.0, now=600.0)
        assert len(s.runs) == 1
        assert s.total_seconds() == 50.0

    def test_roundtrip(self):
        s = BudgetState()
        s.record(30.0, now=9999.0)
        s2 = BudgetState.from_dict(s.to_dict())
        assert s2.total_seconds() == 30.0


# ---------------------------------------------------------------------------
# check_budget / record_budget
# ---------------------------------------------------------------------------

def test_check_budget_ok(tmp_path):
    cfg = BudgetConfig(max_seconds=100.0, window_seconds=3600.0, state_dir=str(tmp_path))
    state = check_budget(cfg, "myjob", now=1000.0)
    assert state.total_seconds() == 0.0


def test_check_budget_raises_when_exhausted(tmp_path):
    cfg = BudgetConfig(max_seconds=10.0, window_seconds=3600.0, state_dir=str(tmp_path))
    record_budget(cfg, "myjob", duration=15.0, now=1000.0)
    with pytest.raises(BudgetExceededError):
        check_budget(cfg, "myjob", now=1500.0)


def test_record_persists(tmp_path):
    cfg = BudgetConfig(max_seconds=3600.0, window_seconds=86400.0, state_dir=str(tmp_path))
    record_budget(cfg, "job", 42.0, now=5000.0)
    state = load_budget_state(cfg, "job")
    assert state.total_seconds() == 42.0
