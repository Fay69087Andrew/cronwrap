"""Tests for cronwrap.watchdog."""
from datetime import datetime, timezone, timedelta
import pytest

from cronwrap.watchdog import (
    WatchdogConfig,
    WatchdogState,
    check_stale,
    watchdog_summary,
)


def _now():
    return datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


class TestWatchdogConfig:
    def test_defaults(self):
        cfg = WatchdogConfig()
        assert cfg.enabled is True
        assert cfg.max_silence_seconds == 3600
        assert cfg.state_dir == "/tmp/cronwrap/watchdog"
        assert cfg.job_name == "default"

    def test_zero_max_silence_raises(self):
        with pytest.raises(ValueError):
            WatchdogConfig(max_silence_seconds=0)

    def test_negative_max_silence_raises(self):
        with pytest.raises(ValueError):
            WatchdogConfig(max_silence_seconds=-1)

    def test_empty_state_dir_raises(self):
        with pytest.raises(ValueError):
            WatchdogConfig(state_dir="   ")

    def test_empty_job_name_raises(self):
        with pytest.raises(ValueError):
            WatchdogConfig(job_name="")

    def test_from_env_defaults(self, monkeypatch):
        for k in ["CRONWRAP_WATCHDOG_ENABLED", "CRONWRAP_WATCHDOG_MAX_SILENCE",
                  "CRONWRAP_WATCHDOG_STATE_DIR", "CRONWRAP_JOB_NAME"]:
            monkeypatch.delenv(k, raising=False)
        cfg = WatchdogConfig.from_env()
        assert cfg.enabled is True
        assert cfg.max_silence_seconds == 3600

    def test_from_env_disabled(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_WATCHDOG_ENABLED", "false")
        cfg = WatchdogConfig.from_env()
        assert cfg.enabled is False


class TestCheckStale:
    def test_never_seen_is_stale(self):
        cfg = WatchdogConfig()
        state = WatchdogState(job_name="job")
        assert check_stale(state, cfg, now=_now()) is True

    def test_recent_is_not_stale(self):
        cfg = WatchdogConfig(max_silence_seconds=3600)
        now = _now()
        state = WatchdogState(job_name="job", last_seen=now - timedelta(seconds=100))
        assert check_stale(state, cfg, now=now) is False

    def test_old_is_stale(self):
        cfg = WatchdogConfig(max_silence_seconds=3600)
        now = _now()
        state = WatchdogState(job_name="job", last_seen=now - timedelta(seconds=7200))
        assert check_stale(state, cfg, now=now) is True

    def test_disabled_never_stale(self):
        cfg = WatchdogConfig(enabled=False)
        state = WatchdogState(job_name="job")
        assert check_stale(state, cfg, now=_now()) is False


class TestWatchdogState:
    def test_roundtrip(self):
        now = _now()
        s = WatchdogState(job_name="myjob", last_seen=now, stale=True)
        d = s.to_dict()
        s2 = WatchdogState.from_dict(d)
        assert s2.job_name == "myjob"
        assert s2.last_seen == now
        assert s2.stale is True

    def test_none_last_seen_roundtrip(self):
        s = WatchdogState(job_name="x")
        s2 = WatchdogState.from_dict(s.to_dict())
        assert s2.last_seen is None


class TestWatchdogSummary:
    def test_disabled(self):
        cfg = WatchdogConfig(enabled=False)
        state = WatchdogState(job_name="x")
        assert "disabled" in watchdog_summary(state, cfg)

    def test_never_seen(self):
        cfg = WatchdogConfig()
        state = WatchdogState(job_name="myjob")
        summary = watchdog_summary(state, cfg)
        assert "never seen" in summary

    def test_stale_shown(self):
        cfg = WatchdogConfig()
        state = WatchdogState(job_name="myjob", last_seen=_now(), stale=True)
        assert "STALE" in watchdog_summary(state, cfg)

    def test_ok_shown(self):
        cfg = WatchdogConfig()
        state = WatchdogState(job_name="myjob", last_seen=_now(), stale=False)
        assert "ok" in watchdog_summary(state, cfg)
