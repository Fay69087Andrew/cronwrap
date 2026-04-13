"""Tests for cronwrap.scheduler."""
from __future__ import annotations

import datetime
import importlib
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Provide a lightweight croniter stub so the tests run without the real package
# ---------------------------------------------------------------------------

class _FakeCroniter:
    """Minimal stub that mimics the parts of croniter used by scheduler.py."""

    _VALID = {"* * * * *", "0 * * * *", "0 9 * * 1", "30 8 * * *"}

    @staticmethod
    def is_valid(expr: str) -> bool:
        return expr in _FakeCroniter._VALID

    def __init__(self, expr: str, base: datetime.datetime) -> None:
        self._expr = expr
        self._current = base

    def get_next(self, type_=datetime.datetime) -> datetime.datetime:
        # Advance by one minute for every call
        self._current = self._current + datetime.timedelta(minutes=1)
        return self._current

    def get_prev(self, type_=datetime.datetime) -> datetime.datetime:
        self._current = self._current - datetime.timedelta(minutes=1)
        return self._current


_stub_module = types.ModuleType("croniter")
_stub_module.croniter = _FakeCroniter  # type: ignore
sys.modules.setdefault("croniter", _stub_module)

from cronwrap import scheduler  # noqa: E402  (import after stub)
from cronwrap.scheduler import ScheduleConfig, is_due, next_run, prev_run


class TestScheduleConfig(unittest.TestCase):
    def test_defaults(self):
        cfg = ScheduleConfig()
        self.assertEqual(cfg.expression, "* * * * *")
        self.assertEqual(cfg.timezone, "UTC")

    def test_valid_expression_accepted(self):
        cfg = ScheduleConfig(expression="0 * * * *")
        self.assertEqual(cfg.expression, "0 * * * *")

    def test_invalid_expression_raises(self):
        with self.assertRaises(ValueError):
            ScheduleConfig(expression="not a cron")


class TestIsDue(unittest.TestCase):
    def test_returns_bool(self):
        cfg = ScheduleConfig()
        now = datetime.datetime(2024, 1, 15, 10, 0, 0)
        result = is_due(cfg, now=now)
        self.assertIsInstance(result, bool)

    def test_uses_utcnow_when_no_now(self):
        cfg = ScheduleConfig()
        # Should not raise
        result = is_due(cfg)
        self.assertIsInstance(result, bool)


class TestNextRun(unittest.TestCase):
    def test_returns_datetime(self):
        cfg = ScheduleConfig()
        after = datetime.datetime(2024, 1, 15, 10, 0, 0)
        result = next_run(cfg, after=after)
        self.assertIsInstance(result, datetime.datetime)

    def test_next_is_after_base(self):
        cfg = ScheduleConfig()
        after = datetime.datetime(2024, 1, 15, 10, 0, 0)
        result = next_run(cfg, after=after)
        self.assertGreater(result, after)


class TestPrevRun(unittest.TestCase):
    def test_returns_datetime(self):
        cfg = ScheduleConfig()
        before = datetime.datetime(2024, 1, 15, 10, 5, 0)
        result = prev_run(cfg, before=before)
        self.assertIsInstance(result, datetime.datetime)

    def test_prev_is_before_base(self):
        cfg = ScheduleConfig()
        before = datetime.datetime(2024, 1, 15, 10, 5, 0)
        result = prev_run(cfg, before=before)
        self.assertLess(result, before)


if __name__ == "__main__":
    unittest.main()
