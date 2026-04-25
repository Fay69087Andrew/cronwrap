"""Tests for cronwrap.surge."""
from __future__ import annotations

import json
import pytest

from cronwrap.surge import (
    SurgeConfig,
    SurgeState,
    check_surge,
    load_surge_state,
    save_surge_state,
    surge_summary,
)


# ---------------------------------------------------------------------------
# SurgeConfig
# ---------------------------------------------------------------------------

class TestSurgeConfig:
    def test_defaults(self):
        cfg = SurgeConfig()
        assert cfg.enabled is True
        assert cfg.threshold_multiplier == 2.0
        assert cfg.window == 10
        assert cfg.state_dir == "/tmp/cronwrap/surge"

    def test_multiplier_at_boundary_raises(self):
        with pytest.raises(ValueError, match="threshold_multiplier"):
            SurgeConfig(threshold_multiplier=1.0)

    def test_multiplier_below_one_raises(self):
        with pytest.raises(ValueError, match="threshold_multiplier"):
            SurgeConfig(threshold_multiplier=0.5)

    def test_zero_window_raises(self):
        with pytest.raises(ValueError, match="window"):
            SurgeConfig(window=0)

    def test_negative_window_raises(self):
        with pytest.raises(ValueError, match="window"):
            SurgeConfig(window=-1)

    def test_empty_state_dir_raises(self):
        with pytest.raises(ValueError, match="state_dir"):
            SurgeConfig(state_dir="")

    def test_from_env_defaults(self, monkeypatch):
        for k in ("CRONWRAP_SURGE_ENABLED", "CRONWRAP_SURGE_THRESHOLD_MULTIPLIER",
                  "CRONWRAP_SURGE_WINDOW", "CRONWRAP_SURGE_STATE_DIR"):
            monkeypatch.delenv(k, raising=False)
        cfg = SurgeConfig.from_env()
        assert cfg.enabled is True
        assert cfg.threshold_multiplier == 2.0

    def test_from_env_custom(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_SURGE_ENABLED", "false")
        monkeypatch.setenv("CRONWRAP_SURGE_THRESHOLD_MULTIPLIER", "3.5")
        monkeypatch.setenv("CRONWRAP_SURGE_WINDOW", "5")
        cfg = SurgeConfig.from_env()
        assert cfg.enabled is False
        assert cfg.threshold_multiplier == 3.5
        assert cfg.window == 5


# ---------------------------------------------------------------------------
# SurgeState
# ---------------------------------------------------------------------------

class TestSurgeState:
    def test_rolling_average_empty(self):
        s = SurgeState()
        assert s.rolling_average(5) is None

    def test_rolling_average_uses_window(self):
        s = SurgeState(durations=[10.0, 10.0, 10.0, 10.0, 100.0])
        avg = s.rolling_average(3)
        # last 3: 10.0, 10.0, 100.0 -> 40.0
        assert avg == pytest.approx(40.0)

    def test_record_trims_history(self):
        s = SurgeState(durations=[1.0] * 25)
        s.record(2.0, window=10)
        assert len(s.durations) <= 21  # window*2 + 1 before trim

    def test_roundtrip_dict(self):
        s = SurgeState(durations=[1.0, 2.0, 3.0])
        s2 = SurgeState.from_dict(s.to_dict())
        assert s2.durations == [1.0, 2.0, 3.0]


# ---------------------------------------------------------------------------
# check_surge / load / save
# ---------------------------------------------------------------------------

def _cfg(tmp_path) -> SurgeConfig:
    return SurgeConfig(state_dir=str(tmp_path))


def test_first_run_no_surge(tmp_path):
    cfg = _cfg(tmp_path)
    is_surge, avg = check_surge(cfg, "job1", 5.0)
    assert is_surge is False
    assert avg is None


def test_surge_detected(tmp_path):
    cfg = _cfg(tmp_path)
    for _ in range(5):
        check_surge(cfg, "job1", 10.0)
    is_surge, avg = check_surge(cfg, "job1", 100.0)
    assert is_surge is True
    assert avg == pytest.approx(10.0)


def test_no_surge_when_within_threshold(tmp_path):
    cfg = _cfg(tmp_path)
    for _ in range(5):
        check_surge(cfg, "job1", 10.0)
    is_surge, avg = check_surge(cfg, "job1", 15.0)
    assert is_surge is False


def test_disabled_never_surges(tmp_path):
    cfg = SurgeConfig(enabled=False, state_dir=str(tmp_path))
    for _ in range(5):
        check_surge(cfg, "job1", 10.0)
    is_surge, avg = check_surge(cfg, "job1", 999.0)
    assert is_surge is False
    assert avg is None


def test_state_persists_across_calls(tmp_path):
    cfg = _cfg(tmp_path)
    for _ in range(3):
        check_surge(cfg, "jobX", 5.0)
    state = load_surge_state(cfg, "jobX")
    assert len(state.durations) == 3


# ---------------------------------------------------------------------------
# surge_summary
# ---------------------------------------------------------------------------

def test_summary_no_baseline():
    msg = surge_summary(False, 3.0, None)
    assert "no baseline" in msg


def test_summary_surge():
    msg = surge_summary(True, 30.0, 10.0)
    assert "YES" in msg
    assert "30.00" in msg


def test_summary_no_surge():
    msg = surge_summary(False, 8.0, 10.0)
    assert "surge=no" in msg
    assert "8.00" in msg
