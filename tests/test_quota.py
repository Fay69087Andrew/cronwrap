"""Tests for cronwrap.quota."""
from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from cronwrap.quota import (
    QuotaConfig,
    QuotaExceededError,
    QuotaState,
    check_quota,
    load_quota_state,
    quota_summary,
    save_quota_state,
)


# ---------------------------------------------------------------------------
# QuotaConfig
# ---------------------------------------------------------------------------

class TestQuotaConfig:
    def test_defaults(self):
        cfg = QuotaConfig()
        assert cfg.max_runs == 0
        assert cfg.window_seconds == 3600
        assert cfg.state_dir == "/tmp/cronwrap/quota"

    def test_negative_max_runs_raises(self):
        with pytest.raises(ValueError, match="max_runs"):
            QuotaConfig(max_runs=-1)

    def test_zero_window_raises(self):
        with pytest.raises(ValueError, match="window_seconds"):
            QuotaConfig(window_seconds=0)

    def test_negative_window_raises(self):
        with pytest.raises(ValueError, match="window_seconds"):
            QuotaConfig(window_seconds=-10)

    def test_empty_state_dir_raises(self):
        with pytest.raises(ValueError, match="state_dir"):
            QuotaConfig(state_dir="")

    def test_from_env_defaults(self):
        with patch.dict("os.environ", {}, clear=False):
            cfg = QuotaConfig.from_env()
        assert cfg.max_runs == 0
        assert cfg.window_seconds == 3600

    def test_from_env_custom(self):
        env = {
            "CRONWRAP_QUOTA_MAX_RUNS": "5",
            "CRONWRAP_QUOTA_WINDOW": "600",
            "CRONWRAP_QUOTA_STATE_DIR": "/tmp/q",
        }
        with patch.dict("os.environ", env):
            cfg = QuotaConfig.from_env()
        assert cfg.max_runs == 5
        assert cfg.window_seconds == 600
        assert cfg.state_dir == "/tmp/q"


# ---------------------------------------------------------------------------
# QuotaState
# ---------------------------------------------------------------------------

class TestQuotaState:
    def test_prune_removes_old(self):
        now = time.time()
        state = QuotaState(timestamps=[now - 200, now - 50, now])
        state.prune(window_seconds=100, now=now)
        assert state.count() == 2

    def test_roundtrip(self):
        state = QuotaState(timestamps=[1.0, 2.0])
        assert QuotaState.from_dict(state.to_dict()).timestamps == [1.0, 2.0]


# ---------------------------------------------------------------------------
# check_quota
# ---------------------------------------------------------------------------

class TestCheckQuota:
    def test_disabled_when_max_runs_zero(self, tmp_path):
        cfg = QuotaConfig(max_runs=0, state_dir=str(tmp_path))
        # Should not raise regardless of how many times called
        for _ in range(20):
            check_quota(cfg, "job1")

    def test_allows_up_to_limit(self, tmp_path):
        cfg = QuotaConfig(max_runs=3, window_seconds=60, state_dir=str(tmp_path))
        now = time.time()
        for i in range(3):
            check_quota(cfg, "jobA", now=now + i)

    def test_raises_when_limit_exceeded(self, tmp_path):
        cfg = QuotaConfig(max_runs=2, window_seconds=60, state_dir=str(tmp_path))
        now = time.time()
        check_quota(cfg, "jobB", now=now)
        check_quota(cfg, "jobB", now=now + 1)
        with pytest.raises(QuotaExceededError, match="jobB"):
            check_quota(cfg, "jobB", now=now + 2)

    def test_resets_after_window(self, tmp_path):
        cfg = QuotaConfig(max_runs=1, window_seconds=60, state_dir=str(tmp_path))
        now = time.time()
        check_quota(cfg, "jobC", now=now)
        # After window expires the old entry is pruned
        check_quota(cfg, "jobC", now=now + 120)

    def test_quota_summary_disabled(self, tmp_path):
        cfg = QuotaConfig(max_runs=0, state_dir=str(tmp_path))
        assert quota_summary(cfg, "jobD") == "quota: disabled"

    def test_quota_summary_shows_count(self, tmp_path):
        cfg = QuotaConfig(max_runs=5, window_seconds=3600, state_dir=str(tmp_path))
        now = time.time()
        check_quota(cfg, "jobE", now=now)
        check_quota(cfg, "jobE", now=now + 1)
        summary = quota_summary(cfg, "jobE", now=now + 2)
        assert "2/5" in summary
