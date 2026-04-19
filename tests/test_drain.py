"""Tests for cronwrap.drain and cronwrap.drain_integration."""
from __future__ import annotations

import pytest

from cronwrap.drain import DrainConfig, DrainResult, wait_for_drain, drain_summary
from cronwrap.drain_integration import build_drain_config, drain_process, report_drain


# ---------------------------------------------------------------------------
# TestDrainConfig
# ---------------------------------------------------------------------------

class TestDrainConfig:
    def test_defaults(self):
        cfg = DrainConfig()
        assert cfg.enabled is True
        assert cfg.window_seconds == 30.0
        assert cfg.poll_interval == 0.5

    def test_zero_window_raises(self):
        with pytest.raises(ValueError, match="window_seconds"):
            DrainConfig(window_seconds=0)

    def test_negative_window_raises(self):
        with pytest.raises(ValueError, match="window_seconds"):
            DrainConfig(window_seconds=-1)

    def test_zero_poll_raises(self):
        with pytest.raises(ValueError, match="poll_interval"):
            DrainConfig(poll_interval=0)

    def test_poll_exceeds_window_raises(self):
        with pytest.raises(ValueError, match="poll_interval"):
            DrainConfig(window_seconds=1.0, poll_interval=2.0)

    def test_from_env_defaults(self, monkeypatch):
        for k in ("CRONWRAP_DRAIN_ENABLED", "CRONWRAP_DRAIN_WINDOW_SECONDS", "CRONWRAP_DRAIN_POLL_INTERVAL"):
            monkeypatch.delenv(k, raising=False)
        cfg = DrainConfig.from_env()
        assert cfg.enabled is True
        assert cfg.window_seconds == 30.0

    def test_from_env_disabled(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_DRAIN_ENABLED", "false")
        cfg = DrainConfig.from_env()
        assert cfg.enabled is False

    def test_from_env_custom_window(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_DRAIN_WINDOW_SECONDS", "60")
        monkeypatch.setenv("CRONWRAP_DRAIN_POLL_INTERVAL", "1")
        cfg = DrainConfig.from_env()
        assert cfg.window_seconds == 60.0


# ---------------------------------------------------------------------------
# TestWaitForDrain
# ---------------------------------------------------------------------------

class TestWaitForDrain:
    def _fake_time(self, values):
        it = iter(values)
        return lambda: next(it)

    def test_disabled_returns_skipped(self):
        cfg = DrainConfig(enabled=False)
        result = wait_for_drain(cfg, lambda: False)
        assert result.drained is False
        assert result.timed_out is False

    def test_done_immediately(self):
        cfg = DrainConfig(window_seconds=5.0, poll_interval=0.1)
        calls = []
        times = iter([0.0, 0.0, 0.05])
        result = wait_for_drain(cfg, lambda: True, _sleep=lambda _: None, _time=lambda: next(times))
        assert result.drained is True
        assert result.timed_out is False

    def test_times_out(self):
        cfg = DrainConfig(window_seconds=1.0, poll_interval=0.5)
        time_vals = iter([0.0, 0.6, 1.1])
        result = wait_for_drain(
            cfg,
            lambda: False,
            _sleep=lambda _: None,
            _time=lambda: next(time_vals),
        )
        assert result.timed_out is True
        assert result.drained is False

    def test_str_representation(self):
        r = DrainResult(drained=True, elapsed_seconds=1.5, timed_out=False)
        assert "drained" in str(r)
        assert "1.50" in str(r)


# ---------------------------------------------------------------------------
# TestDrainIntegration
# ---------------------------------------------------------------------------

class _FakeProc:
    def __init__(self, done_after: int):
        self._calls = 0
        self._done_after = done_after

    def poll(self):
        self._calls += 1
        return 0 if self._calls >= self._done_after else None


class TestDrainIntegration:
    def test_build_drain_config_returns_config(self, monkeypatch):
        monkeypatch.delenv("CRONWRAP_DRAIN_ENABLED", raising=False)
        cfg = build_drain_config()
        assert isinstance(cfg, DrainConfig)

    def test_drain_process_completes(self):
        cfg = DrainConfig(window_seconds=5.0, poll_interval=0.01)
        proc = _FakeProc(done_after=2)
        result = drain_process(cfg, proc)
        assert result.drained is True

    def test_report_drain_returns_string(self):
        r = DrainResult(drained=False, elapsed_seconds=30.0, timed_out=True)
        s = report_drain(r)
        assert isinstance(s, str)
        assert "timed_out" in s
