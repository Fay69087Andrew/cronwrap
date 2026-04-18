"""Tests for cronwrap.watchdog_integration."""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
import pytest

from cronwrap.watchdog import WatchdogConfig, WatchdogState
from cronwrap.watchdog_integration import (
    load_watchdog_state,
    save_watchdog_state,
    ping_watchdog,
    check_watchdog_or_warn,
)


def _cfg(tmp_path) -> WatchdogConfig:
    return WatchdogConfig(state_dir=str(tmp_path), job_name="testjob")


def _now():
    return datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


class TestLoadSave:
    def test_load_returns_empty_state_when_missing(self, tmp_path):
        cfg = _cfg(tmp_path)
        state = load_watchdog_state(cfg)
        assert state.last_seen is None
        assert state.job_name == "testjob"

    def test_save_and_load_roundtrip(self, tmp_path):
        cfg = _cfg(tmp_path)
        now = _now()
        state = WatchdogState(job_name="testjob", last_seen=now, stale=False)
        save_watchdog_state(state, cfg)
        loaded = load_watchdog_state(cfg)
        assert loaded.last_seen == now
        assert loaded.stale is False

    def test_save_creates_parent_dirs(self, tmp_path):
        cfg = WatchdogConfig(state_dir=str(tmp_path / "deep" / "dir"), job_name="j")
        state = WatchdogState(job_name="j", last_seen=_now())
        save_watchdog_state(state, cfg)
        assert (tmp_path / "deep" / "dir" / "j.json").exists()


class TestPingWatchdog:
    def test_ping_writes_state(self, tmp_path):
        cfg = _cfg(tmp_path)
        now = _now()
        state = ping_watchdog(cfg, now=now)
        assert state.last_seen == now
        assert state.stale is False
        loaded = load_watchdog_state(cfg)
        assert loaded.last_seen == now

    def test_ping_overwrites_old(self, tmp_path):
        cfg = _cfg(tmp_path)
        old = _now() - timedelta(hours=5)
        ping_watchdog(cfg, now=old)
        new = _now()
        ping_watchdog(cfg, now=new)
        loaded = load_watchdog_state(cfg)
        assert loaded.last_seen == new


class TestCheckWatchdogOrWarn:
    def test_stale_when_never_seen(self, tmp_path):
        cfg = _cfg(tmp_path)
        state, stale = check_watchdog_or_warn(cfg, now=_now())
        assert stale is True
        assert state.stale is True

    def test_not_stale_when_recent(self, tmp_path):
        cfg = _cfg(tmp_path)
        now = _now()
        ping_watchdog(cfg, now=now - timedelta(seconds=60))
        state, stale = check_watchdog_or_warn(cfg, now=now)
        assert stale is False

    def test_stale_when_old(self, tmp_path):
        cfg = _cfg(tmp_path)
        now = _now()
        ping_watchdog(cfg, now=now - timedelta(hours=2))
        state, stale = check_watchdog_or_warn(cfg, now=now)
        assert stale is True
