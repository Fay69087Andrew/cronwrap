"""Tests for cronwrap.ratelimit."""

import json
import os
import pytest

from cronwrap.ratelimit import (
    RateLimitConfig,
    RateLimitState,
    _state_path,
    is_allowed,
    remaining_alerts,
)


# ---------------------------------------------------------------------------
# RateLimitConfig
# ---------------------------------------------------------------------------

class TestRateLimitConfig:
    def test_defaults(self):
        cfg = RateLimitConfig()
        assert cfg.window_seconds == 3600
        assert cfg.max_alerts == 5

    def test_zero_window_raises(self):
        with pytest.raises(ValueError, match="window_seconds"):
            RateLimitConfig(window_seconds=0)

    def test_negative_window_raises(self):
        with pytest.raises(ValueError, match="window_seconds"):
            RateLimitConfig(window_seconds=-1)

    def test_zero_max_alerts_raises(self):
        with pytest.raises(ValueError, match="max_alerts"):
            RateLimitConfig(max_alerts=0)

    def test_from_env(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_RATELIMIT_WINDOW", "120")
        monkeypatch.setenv("CRONWRAP_RATELIMIT_MAX_ALERTS", "3")
        monkeypatch.setenv("CRONWRAP_RATELIMIT_STATE_DIR", "/tmp/test")
        cfg = RateLimitConfig.from_env()
        assert cfg.window_seconds == 120
        assert cfg.max_alerts == 3
        assert cfg.state_dir == "/tmp/test"


# ---------------------------------------------------------------------------
# RateLimitState
# ---------------------------------------------------------------------------

class TestRateLimitState:
    def test_roundtrip(self):
        state = RateLimitState(timestamps=[1.0, 2.0, 3.0])
        assert RateLimitState.from_dict(state.to_dict()).timestamps == [1.0, 2.0, 3.0]

    def test_empty_from_dict(self):
        state = RateLimitState.from_dict({})
        assert state.timestamps == []


# ---------------------------------------------------------------------------
# is_allowed
# ---------------------------------------------------------------------------

class TestIsAllowed:
    def _cfg(self, tmp_path, max_alerts=3, window=60):
        return RateLimitConfig(
            max_alerts=max_alerts, window_seconds=window, state_dir=str(tmp_path)
        )

    def test_first_alert_allowed(self, tmp_path):
        assert is_allowed("job1", self._cfg(tmp_path), now=1000.0) is True

    def test_up_to_max_allowed(self, tmp_path):
        cfg = self._cfg(tmp_path, max_alerts=3)
        for _ in range(3):
            assert is_allowed("job1", cfg, now=1000.0) is True

    def test_exceeding_max_blocked(self, tmp_path):
        cfg = self._cfg(tmp_path, max_alerts=3)
        for _ in range(3):
            is_allowed("job1", cfg, now=1000.0)
        assert is_allowed("job1", cfg, now=1001.0) is False

    def test_old_timestamps_expire(self, tmp_path):
        cfg = self._cfg(tmp_path, max_alerts=2, window=60)
        is_allowed("job1", cfg, now=1000.0)
        is_allowed("job1", cfg, now=1001.0)
        # Both timestamps are now outside the window
        assert is_allowed("job1", cfg, now=1200.0) is True

    def test_state_persisted(self, tmp_path):
        cfg = self._cfg(tmp_path, max_alerts=2)
        is_allowed("job1", cfg, now=1000.0)
        path = _state_path(str(tmp_path), "job1")
        data = json.loads(path.read_text())
        assert len(data["timestamps"]) == 1


# ---------------------------------------------------------------------------
# remaining_alerts
# ---------------------------------------------------------------------------

class TestRemainingAlerts:
    def _cfg(self, tmp_path, max_alerts=5, window=60):
        return RateLimitConfig(
            max_alerts=max_alerts, window_seconds=window, state_dir=str(tmp_path)
        )

    def test_full_remaining_when_empty(self, tmp_path):
        assert remaining_alerts("job", self._cfg(tmp_path), now=1000.0) == 5

    def test_decrements_after_alert(self, tmp_path):
        cfg = self._cfg(tmp_path, max_alerts=5)
        is_allowed("job", cfg, now=1000.0)
        assert remaining_alerts("job", cfg, now=1000.0) == 4

    def test_zero_when_exhausted(self, tmp_path):
        cfg = self._cfg(tmp_path, max_alerts=2)
        is_allowed("job", cfg, now=1000.0)
        is_allowed("job", cfg, now=1001.0)
        assert remaining_alerts("job", cfg, now=1002.0) == 0
