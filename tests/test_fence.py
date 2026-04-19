"""Tests for cronwrap.fence."""
from __future__ import annotations

import pytest
from datetime import time, datetime, timezone
from unittest.mock import patch

from cronwrap.fence import (
    FenceConfig,
    FenceViolationError,
    is_within_fence,
    check_fence_or_abort,
    fence_summary,
)


class TestFenceConfig:
    def test_defaults(self):
        cfg = FenceConfig()
        assert cfg.enabled is False
        assert cfg.window_start == time(0, 0)
        assert cfg.window_end == time(23, 59)
        assert cfg.timezone_name == "UTC"

    def test_start_after_end_raises(self):
        with pytest.raises(ValueError, match="before"):
            FenceConfig(window_start=time(22, 0), window_end=time(8, 0))

    def test_start_equal_end_raises(self):
        with pytest.raises(ValueError):
            FenceConfig(window_start=time(9, 0), window_end=time(9, 0))

    def test_empty_timezone_raises(self):
        with pytest.raises(ValueError, match="timezone_name"):
            FenceConfig(window_start=time(0, 0), window_end=time(12, 0), timezone_name="")

    def test_invalid_start_type_raises(self):
        with pytest.raises(TypeError):
            FenceConfig(window_start="09:00", window_end=time(17, 0))  # type: ignore

    def test_from_env_defaults(self, monkeypatch):
        for key in ("CRONWRAP_FENCE_ENABLED", "CRONWRAP_FENCE_START", "CRONWRAP_FENCE_END", "CRONWRAP_FENCE_TIMEZONE"):
            monkeypatch.delenv(key, raising=False)
        cfg = FenceConfig.from_env()
        assert cfg.enabled is False
        assert cfg.timezone_name == "UTC"

    def test_from_env_custom(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_FENCE_ENABLED", "true")
        monkeypatch.setenv("CRONWRAP_FENCE_START", "08:00")
        monkeypatch.setenv("CRONWRAP_FENCE_END", "18:00")
        monkeypatch.setenv("CRONWRAP_FENCE_TIMEZONE", "Europe/London")
        cfg = FenceConfig.from_env()
        assert cfg.enabled is True
        assert cfg.window_start == time(8, 0)
        assert cfg.window_end == time(18, 0)
        assert cfg.timezone_name == "Europe/London"


class TestIsWithinFence:
    def _now(self, h: int, m: int) -> datetime:
        return datetime(2024, 1, 15, h, m, 0, tzinfo=timezone.utc)

    def test_disabled_always_within(self):
        cfg = FenceConfig(enabled=False, window_start=time(9, 0), window_end=time(10, 0))
        assert is_within_fence(cfg, self._now(23, 0)) is True

    def test_within_window(self):
        cfg = FenceConfig(enabled=True, window_start=time(8, 0), window_end=time(18, 0))
        assert is_within_fence(cfg, self._now(12, 0)) is True

    def test_before_window(self):
        cfg = FenceConfig(enabled=True, window_start=time(8, 0), window_end=time(18, 0))
        assert is_within_fence(cfg, self._now(7, 59)) is False

    def test_after_window(self):
        cfg = FenceConfig(enabled=True, window_start=time(8, 0), window_end=time(18, 0))
        assert is_within_fence(cfg, self._now(18, 1)) is False

    def test_at_boundary_start(self):
        cfg = FenceConfig(enabled=True, window_start=time(8, 0), window_end=time(18, 0))
        assert is_within_fence(cfg, self._now(8, 0)) is True


class TestCheckFenceOrAbort:
    def test_does_not_raise_when_within(self):
        cfg = FenceConfig(enabled=True, window_start=time(0, 0), window_end=time(23, 59))
        check_fence_or_abort(cfg, datetime(2024, 1, 15, 12, 0, tzinfo=timezone.utc))

    def test_raises_system_exit_when_outside(self):
        cfg = FenceConfig(enabled=True, window_start=time(9, 0), window_end=time(10, 0))
        with pytest.raises(SystemExit):
            check_fence_or_abort(cfg, datetime(2024, 1, 15, 23, 0, tzinfo=timezone.utc))


class TestFenceSummary:
    def test_includes_status_allowed(self):
        cfg = FenceConfig(enabled=True, window_start=time(0, 0), window_end=time(23, 59))
        summary = fence_summary(cfg, datetime(2024, 1, 15, 12, 0, tzinfo=timezone.utc))
        assert "allowed" in summary

    def test_includes_status_blocked(self):
        cfg = FenceConfig(enabled=True, window_start=time(9, 0), window_end=time(10, 0))
        summary = fence_summary(cfg, datetime(2024, 1, 15, 23, 0, tzinfo=timezone.utc))
        assert "blocked" in summary

    def test_includes_window(self):
        cfg = FenceConfig(enabled=True, window_start=time(8, 0), window_end=time(17, 0))
        summary = fence_summary(cfg, datetime(2024, 1, 15, 12, 0, tzinfo=timezone.utc))
        assert "08:00" in summary
        assert "17:00" in summary
