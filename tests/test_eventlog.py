"""Tests for cronwrap.eventlog and cronwrap.eventlog_integration."""
import os
import pytest
from unittest.mock import MagicMock

from cronwrap.eventlog import EventLogConfig, EventLog, Event
from cronwrap.eventlog_integration import build_event_log, record_run_events, eventlog_summary


class TestEventLogConfig:
    def test_defaults(self):
        cfg = EventLogConfig()
        assert cfg.enabled is True
        assert cfg.max_events == 200
        assert cfg.level == "info"

    def test_level_lowercased(self):
        cfg = EventLogConfig(level="WARNING")
        assert cfg.level == "warning"

    def test_invalid_level_raises(self):
        with pytest.raises(ValueError, match="level must be one of"):
            EventLogConfig(level="verbose")

    def test_zero_max_events_raises(self):
        with pytest.raises(ValueError, match="max_events"):
            EventLogConfig(max_events=0)

    def test_negative_max_events_raises(self):
        with pytest.raises(ValueError):
            EventLogConfig(max_events=-1)

    def test_from_env_defaults(self, monkeypatch):
        for k in ("CRONWRAP_EVENTLOG_ENABLED", "CRONWRAP_EVENTLOG_MAX_EVENTS", "CRONWRAP_EVENTLOG_LEVEL"):
            monkeypatch.delenv(k, raising=False)
        cfg = EventLogConfig.from_env()
        assert cfg.enabled is True
        assert cfg.max_events == 200
        assert cfg.level == "info"

    def test_from_env_disabled(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_EVENTLOG_ENABLED", "false")
        cfg = EventLogConfig.from_env()
        assert cfg.enabled is False

    def test_from_env_custom(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_EVENTLOG_MAX_EVENTS", "50")
        monkeypatch.setenv("CRONWRAP_EVENTLOG_LEVEL", "debug")
        cfg = EventLogConfig.from_env()
        assert cfg.max_events == 50
        assert cfg.level == "debug"


class TestEventLog:
    def _log(self):
        return EventLog(config=EventLogConfig())

    def test_record_adds_event(self):
        log = self._log()
        log.record("test.event", "hello")
        assert len(log.events) == 1
        assert log.events[0].name == "test.event"

    def test_disabled_log_records_nothing(self):
        log = EventLog(config=EventLogConfig(enabled=False))
        log.record("x", "y")
        assert log.events == []

    def test_max_events_cap(self):
        log = EventLog(config=EventLogConfig(max_events=3))
        for i in range(10):
            log.record("e", str(i))
        assert len(log.events) == 3

    def test_by_level_filters(self):
        log = self._log()
        log.record("a", "msg", level="info")
        log.record("b", "msg", level="error")
        assert len(log.by_level("info")) == 1
        assert len(log.by_level("error")) == 1
        assert log.by_level("debug") == []

    def test_summary_counts(self):
        log = self._log()
        log.record("a", "m", level="info")
        log.record("b", "m", level="info")
        log.record("c", "m", level="error")
        s = log.summary()
        assert s["total"] == 3
        assert s["by_level"]["info"] == 2
        assert s["by_level"]["error"] == 1

    def test_event_to_dict_keys(self):
        log = self._log()
        log.record("x", "msg", data={"k": "v"})
        d = log.events[0].to_dict()
        assert set(d.keys()) == {"name", "level", "message", "timestamp", "data"}
        assert d["data"] == {"k": "v"}


def _make_result(exit_code=0, command="echo hi", duration=1.5):
    r = MagicMock()
    r.exit_code = exit_code
    r.success = exit_code == 0
    r.command = command
    r.duration_seconds = duration
    return r


class TestEventLogIntegration:
    def test_record_run_events_success(self):
        log = EventLog()
        record_run_events(log, _make_result(0))
        names = [e.name for e in log.events]
        assert "job.start" in names
        assert "job.finish" in names
        assert "job.duration" in names

    def test_record_run_events_failure_level(self):
        log = EventLog()
        record_run_events(log, _make_result(1))
        finish = next(e for e in log.events if e.name == "job.finish")
        assert finish.level == "error"

    def test_eventlog_summary_format(self):
        log = EventLog()
        log.record("a", "m", level="info")
        log.record("b", "m", level="error")
        s = eventlog_summary(log)
        assert s.startswith("EventLog(")
        assert "total=2" in s

    def test_build_event_log_returns_event_log(self, monkeypatch):
        monkeypatch.delenv("CRONWRAP_EVENTLOG_ENABLED", raising=False)
        log = build_event_log()
        assert isinstance(log, EventLog)
