"""Tests for cronwrap.throttle."""

from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from cronwrap.throttle import (
    ThrottleConfig,
    ThrottleState,
    _state_path,
    load_state,
    record_success,
    save_state,
    should_throttle,
)


# ---------------------------------------------------------------------------
# ThrottleConfig
# ---------------------------------------------------------------------------

class TestThrottleConfig:
    def test_defaults(self):
        cfg = ThrottleConfig()
        assert cfg.min_interval == 0
        assert cfg.state_dir == "/tmp/cronwrap/throttle"
        assert cfg.enabled is True

    def test_negative_interval_raises(self):
        with pytest.raises(ValueError, match="min_interval"):
            ThrottleConfig(min_interval=-1)

    def test_empty_state_dir_raises(self):
        with pytest.raises(ValueError, match="state_dir"):
            ThrottleConfig(state_dir="")

    def test_from_env_defaults(self, monkeypatch):
        monkeypatch.delenv("CRONWRAP_THROTTLE_ENABLED", raising=False)
        monkeypatch.delenv("CRONWRAP_THROTTLE_MIN_INTERVAL", raising=False)
        monkeypatch.delenv("CRONWRAP_THROTTLE_STATE_DIR", raising=False)
        cfg = ThrottleConfig.from_env()
        assert cfg.min_interval == 0
        assert cfg.enabled is True

    def test_from_env_custom(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_THROTTLE_ENABLED", "false")
        monkeypatch.setenv("CRONWRAP_THROTTLE_MIN_INTERVAL", "300")
        monkeypatch.setenv("CRONWRAP_THROTTLE_STATE_DIR", "/var/run/cw")
        cfg = ThrottleConfig.from_env()
        assert cfg.enabled is False
        assert cfg.min_interval == 300
        assert cfg.state_dir == "/var/run/cw"


# ---------------------------------------------------------------------------
# ThrottleState
# ---------------------------------------------------------------------------

class TestThrottleState:
    def test_roundtrip(self):
        s = ThrottleState(job_id="backup", last_success_ts=1_700_000_000.0)
        assert ThrottleState.from_dict(s.to_dict()) == s

    def test_missing_ts_defaults_none(self):
        s = ThrottleState.from_dict({"job_id": "x"})
        assert s.last_success_ts is None


# ---------------------------------------------------------------------------
# should_throttle
# ---------------------------------------------------------------------------

class TestShouldThrottle:
    def test_disabled_never_throttles(self):
        cfg = ThrottleConfig(enabled=False, min_interval=60)
        state = ThrottleState(job_id="j", last_success_ts=time.time())
        assert should_throttle(cfg, state) is False

    def test_zero_interval_never_throttles(self):
        cfg = ThrottleConfig(min_interval=0)
        state = ThrottleState(job_id="j", last_success_ts=time.time())
        assert should_throttle(cfg, state) is False

    def test_no_previous_run_not_throttled(self):
        cfg = ThrottleConfig(min_interval=60)
        state = ThrottleState(job_id="j")
        assert should_throttle(cfg, state) is False

    def test_recent_success_throttled(self):
        cfg = ThrottleConfig(min_interval=3600)
        state = ThrottleState(job_id="j", last_success_ts=time.time() - 60)
        assert should_throttle(cfg, state) is True

    def test_old_success_not_throttled(self):
        cfg = ThrottleConfig(min_interval=60)
        state = ThrottleState(job_id="j", last_success_ts=time.time() - 120)
        assert should_throttle(cfg, state) is False


# ---------------------------------------------------------------------------
# load_state / save_state / record_success
# ---------------------------------------------------------------------------

class TestPersistence:
    def test_save_and_load(self, tmp_path):
        cfg = ThrottleConfig(state_dir=str(tmp_path))
        state = ThrottleState(job_id="myjob", last_success_ts=1234.5)
        save_state(cfg, state)
        loaded = load_state(cfg, "myjob")
        assert loaded.last_success_ts == pytest.approx(1234.5)

    def test_load_missing_returns_empty(self, tmp_path):
        cfg = ThrottleConfig(state_dir=str(tmp_path))
        state = load_state(cfg, "nonexistent")
        assert state.last_success_ts is None

    def test_record_success_updates_ts(self, tmp_path):
        cfg = ThrottleConfig(state_dir=str(tmp_path))
        before = time.time()
        state = record_success(cfg, "backup")
        assert state.last_success_ts >= before
        # persisted
        loaded = load_state(cfg, "backup")
        assert loaded.last_success_ts == pytest.approx(state.last_success_ts, abs=0.01)
