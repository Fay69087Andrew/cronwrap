"""Tests for cronwrap.cooldown and cronwrap.cooldown_integration."""
from __future__ import annotations

import sys
import pytest

from cronwrap.cooldown import (
    CooldownConfig,
    CooldownState,
    cooldown_summary,
    is_cooling_down,
    load_state,
    record_run,
    save_state,
)
from cronwrap.cooldown_integration import check_cooldown_or_abort, run_with_cooldown
from cronwrap.runner import RunResult


# ---------------------------------------------------------------------------
# TestCooldownConfig
# ---------------------------------------------------------------------------

class TestCooldownConfig:
    def test_defaults(self):
        cfg = CooldownConfig()
        assert cfg.enabled is False
        assert cfg.min_interval == 60.0
        assert cfg.state_dir == "/tmp/cronwrap/cooldown"

    def test_zero_min_interval_raises(self):
        with pytest.raises(ValueError, match="min_interval"):
            CooldownConfig(min_interval=0)

    def test_negative_min_interval_raises(self):
        with pytest.raises(ValueError, match="min_interval"):
            CooldownConfig(min_interval=-5)

    def test_empty_state_dir_raises(self):
        with pytest.raises(ValueError, match="state_dir"):
            CooldownConfig(state_dir="")

    def test_from_env_defaults(self, monkeypatch):
        for k in ("CRONWRAP_COOLDOWN_ENABLED", "CRONWRAP_COOLDOWN_MIN_INTERVAL", "CRONWRAP_COOLDOWN_STATE_DIR"):
            monkeypatch.delenv(k, raising=False)
        cfg = CooldownConfig.from_env()
        assert cfg.enabled is False
        assert cfg.min_interval == 60.0

    def test_from_env_custom(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_COOLDOWN_ENABLED", "true")
        monkeypatch.setenv("CRONWRAP_COOLDOWN_MIN_INTERVAL", "120")
        cfg = CooldownConfig.from_env()
        assert cfg.enabled is True
        assert cfg.min_interval == 120.0


# ---------------------------------------------------------------------------
# TestCooldownState
# ---------------------------------------------------------------------------

class TestCooldownState:
    def test_roundtrip(self):
        s = CooldownState(last_run=1234567890.0)
        assert CooldownState.from_dict(s.to_dict()).last_run == 1234567890.0

    def test_default_last_run_zero(self):
        assert CooldownState().last_run == 0.0


# ---------------------------------------------------------------------------
# is_cooling_down / record_run
# ---------------------------------------------------------------------------

def _cfg(tmp_path):
    return CooldownConfig(enabled=True, min_interval=30.0, state_dir=str(tmp_path))


def test_not_cooling_when_disabled(tmp_path):
    cfg = CooldownConfig(enabled=False, min_interval=30.0, state_dir=str(tmp_path))
    record_run(cfg, "job1", now=1000.0)
    assert is_cooling_down(cfg, "job1", now=1010.0) is False


def test_cooling_down_within_window(tmp_path):
    cfg = _cfg(tmp_path)
    record_run(cfg, "job1", now=1000.0)
    assert is_cooling_down(cfg, "job1", now=1020.0) is True


def test_not_cooling_after_window(tmp_path):
    cfg = _cfg(tmp_path)
    record_run(cfg, "job1", now=1000.0)
    assert is_cooling_down(cfg, "job1", now=1031.0) is False


def test_cooldown_summary_contains_job_id(tmp_path):
    cfg = _cfg(tmp_path)
    record_run(cfg, "myjob", now=1000.0)
    summary = cooldown_summary(cfg, "myjob", now=1010.0)
    assert "myjob" in summary
    assert "remaining" in summary


# ---------------------------------------------------------------------------
# Integration
# ---------------------------------------------------------------------------

def _ok_result():
    return RunResult(command="echo hi", returncode=0, stdout=b"", stderr=b"", duration=0.1)


def test_check_cooldown_or_abort_raises_when_cooling(tmp_path):
    cfg = _cfg(tmp_path)
    record_run(cfg, "j", now=1000.0)
    with pytest.raises(SystemExit) as exc_info:
        check_cooldown_or_abort(cfg, "j", now=1010.0)
    assert exc_info.value.code == 0


def test_check_cooldown_or_abort_passes_when_clear(tmp_path):
    cfg = _cfg(tmp_path)
    record_run(cfg, "j", now=1000.0)
    check_cooldown_or_abort(cfg, "j", now=1031.0)  # should not raise


def test_run_with_cooldown_records_run(tmp_path):
    cfg = _cfg(tmp_path)
    result, summary = run_with_cooldown(cfg, "j", _ok_result, now=2000.0)
    assert result.returncode == 0
    state = load_state(cfg, "j")
    assert state.last_run == 2000.0
    assert "j" in summary
