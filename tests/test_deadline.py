"""Tests for cronwrap.deadline and cronwrap.deadline_integration."""
from __future__ import annotations

import sys
from datetime import datetime, timezone, timedelta

import pytest

from cronwrap.deadline import (
    DeadlineConfig,
    DeadlineExceededError,
    check_deadline,
    deadline_summary,
)
from cronwrap.deadline_integration import check_deadline_or_abort, deadline_report


_FUTURE = datetime.now(tz=timezone.utc) + timedelta(hours=1)
_PAST = datetime.now(tz=timezone.utc) - timedelta(hours=1)


class TestDeadlineConfig:
    def test_defaults(self):
        cfg = DeadlineConfig()
        assert cfg.deadline is None
        assert cfg.enabled is True

    def test_valid_future_deadline(self):
        cfg = DeadlineConfig(deadline=_FUTURE)
        assert cfg.deadline == _FUTURE

    def test_naive_datetime_raises(self):
        with pytest.raises(ValueError, match="timezone-aware"):
            DeadlineConfig(deadline=datetime(2025, 1, 1))

    def test_non_datetime_raises(self):
        with pytest.raises(TypeError):
            DeadlineConfig(deadline="2025-01-01T00:00:00+00:00")  # type: ignore

    def test_from_env_defaults(self, monkeypatch):
        monkeypatch.delenv("CRONWRAP_DEADLINE", raising=False)
        monkeypatch.delenv("CRONWRAP_DEADLINE_ENABLED", raising=False)
        cfg = DeadlineConfig.from_env()
        assert cfg.deadline is None
        assert cfg.enabled is True

    def test_from_env_disabled(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_DEADLINE_ENABLED", "false")
        monkeypatch.delenv("CRONWRAP_DEADLINE", raising=False)
        cfg = DeadlineConfig.from_env()
        assert cfg.enabled is False

    def test_from_env_parses_deadline(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_DEADLINE", "2099-06-01T12:00:00+00:00")
        monkeypatch.delenv("CRONWRAP_DEADLINE_ENABLED", raising=False)
        cfg = DeadlineConfig.from_env()
        assert cfg.deadline is not None
        assert cfg.deadline.year == 2099

    def test_from_env_naive_iso_raises(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_DEADLINE", "2099-06-01T12:00:00")
        with pytest.raises(ValueError, match="timezone"):
            DeadlineConfig.from_env()


class TestCheckDeadline:
    def test_does_not_raise_when_disabled(self):
        cfg = DeadlineConfig(deadline=_PAST, enabled=False)
        check_deadline(cfg)  # should not raise

    def test_does_not_raise_when_no_deadline(self):
        cfg = DeadlineConfig()
        check_deadline(cfg)

    def test_does_not_raise_before_deadline(self):
        cfg = DeadlineConfig(deadline=_FUTURE)
        check_deadline(cfg)

    def test_raises_after_deadline(self):
        cfg = DeadlineConfig(deadline=_PAST)
        with pytest.raises(DeadlineExceededError):
            check_deadline(cfg)


class TestDeadlineSummary:
    def test_disabled_message(self):
        assert deadline_summary(DeadlineConfig()) == "deadline: disabled"

    def test_shows_deadline(self):
        cfg = DeadlineConfig(deadline=_FUTURE)
        assert "deadline:" in deadline_summary(cfg)


class TestCheckDeadlineOrAbort:
    def test_does_not_exit_for_future(self):
        cfg = DeadlineConfig(deadline=_FUTURE)
        check_deadline_or_abort(cfg)  # should not raise SystemExit

    def test_exits_for_past(self):
        cfg = DeadlineConfig(deadline=_PAST)
        with pytest.raises(SystemExit) as exc_info:
            check_deadline_or_abort(cfg)
        assert exc_info.value.code == 1


class TestDeadlineReport:
    def test_keys_present(self):
        cfg = DeadlineConfig(deadline=_FUTURE)
        report = deadline_report(cfg)
        assert "deadline_enabled" in report
        assert "deadline" in report
        assert "summary" in report

    def test_none_deadline_serialises(self):
        cfg = DeadlineConfig()
        report = deadline_report(cfg)
        assert report["deadline"] is None
