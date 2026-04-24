"""Tests for cronwrap.limiter."""
from __future__ import annotations

import pytest

from cronwrap.limiter import LimiterConfig, limit_lines, limiter_summary


# ---------------------------------------------------------------------------
# TestLimiterConfig
# ---------------------------------------------------------------------------


class TestLimiterConfig:
    def test_defaults(self):
        cfg = LimiterConfig()
        assert cfg.max_lines == 500
        assert cfg.tail is True
        assert cfg.enabled is True
        assert cfg.ellipsis == "... (output truncated)"

    def test_zero_max_lines_raises(self):
        with pytest.raises(ValueError, match="max_lines"):
            LimiterConfig(max_lines=0)

    def test_negative_max_lines_raises(self):
        with pytest.raises(ValueError, match="max_lines"):
            LimiterConfig(max_lines=-1)

    def test_empty_ellipsis_raises(self):
        with pytest.raises(ValueError, match="ellipsis"):
            LimiterConfig(ellipsis="")

    def test_invalid_enabled_raises(self):
        with pytest.raises(TypeError, match="enabled"):
            LimiterConfig(enabled="yes")  # type: ignore[arg-type]

    def test_from_env_defaults(self, monkeypatch):
        for key in (
            "CRONWRAP_LIMITER_ENABLED",
            "CRONWRAP_LIMITER_MAX_LINES",
            "CRONWRAP_LIMITER_TAIL",
            "CRONWRAP_LIMITER_ELLIPSIS",
        ):
            monkeypatch.delenv(key, raising=False)
        cfg = LimiterConfig.from_env()
        assert cfg.max_lines == 500
        assert cfg.tail is True
        assert cfg.enabled is True

    def test_from_env_custom(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_LIMITER_MAX_LINES", "100")
        monkeypatch.setenv("CRONWRAP_LIMITER_TAIL", "false")
        monkeypatch.setenv("CRONWRAP_LIMITER_ENABLED", "1")
        cfg = LimiterConfig.from_env()
        assert cfg.max_lines == 100
        assert cfg.tail is False
        assert cfg.enabled is True

    def test_from_env_disabled(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_LIMITER_ENABLED", "false")
        cfg = LimiterConfig.from_env()
        assert cfg.enabled is False


# ---------------------------------------------------------------------------
# TestLimitLines
# ---------------------------------------------------------------------------


def _make_text(n: int) -> str:
    return "\n".join(f"line {i}" for i in range(1, n + 1))


class TestLimitLines:
    def test_short_text_unchanged(self):
        cfg = LimiterConfig(max_lines=10)
        text = _make_text(5)
        assert limit_lines(text, cfg) == text

    def test_exact_limit_unchanged(self):
        cfg = LimiterConfig(max_lines=5)
        text = _make_text(5)
        assert limit_lines(text, cfg) == text

    def test_tail_keeps_last_lines(self):
        cfg = LimiterConfig(max_lines=3, tail=True)
        text = _make_text(6)
        result = limit_lines(text, cfg)
        assert "line 4" in result
        assert "line 5" in result
        assert "line 6" in result
        assert "line 1" not in result
        assert cfg.ellipsis in result

    def test_head_keeps_first_lines(self):
        cfg = LimiterConfig(max_lines=3, tail=False)
        text = _make_text(6)
        result = limit_lines(text, cfg)
        assert "line 1" in result
        assert "line 2" in result
        assert "line 3" in result
        assert "line 6" not in result
        assert cfg.ellipsis in result

    def test_disabled_returns_full_text(self):
        cfg = LimiterConfig(max_lines=2, enabled=False)
        text = _make_text(10)
        assert limit_lines(text, cfg) == text

    def test_empty_string_returned_unchanged(self):
        cfg = LimiterConfig(max_lines=5)
        assert limit_lines("", cfg) == ""


# ---------------------------------------------------------------------------
# TestLimiterSummary
# ---------------------------------------------------------------------------


class TestLimiterSummary:
    def test_disabled_summary(self):
        cfg = LimiterConfig(enabled=False)
        assert limiter_summary(cfg) == "limiter disabled"

    def test_tail_summary(self):
        cfg = LimiterConfig(max_lines=200, tail=True)
        summary = limiter_summary(cfg)
        assert "200" in summary
        assert "tail" in summary

    def test_head_summary(self):
        cfg = LimiterConfig(max_lines=50, tail=False)
        summary = limiter_summary(cfg)
        assert "50" in summary
        assert "head" in summary
