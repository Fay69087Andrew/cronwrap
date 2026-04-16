"""Tests for cronwrap.banner."""
from __future__ import annotations

import pytest
from datetime import datetime, timezone
from unittest.mock import patch

from cronwrap.banner import BannerConfig, render_banner


class TestBannerConfig:
    def test_defaults(self):
        cfg = BannerConfig()
        assert cfg.enabled is True
        assert cfg.width == 72
        assert cfg.char == "="
        assert cfg.show_timestamp is True
        assert cfg.show_pid is True
        assert cfg.label == "CRONWRAP"

    def test_label_uppercased(self):
        cfg = BannerConfig(label="myjob")
        assert cfg.label == "MYJOB"

    def test_width_too_small_raises(self):
        with pytest.raises(ValueError, match="at least 20"):
            BannerConfig(width=5)

    def test_width_too_large_raises(self):
        with pytest.raises(ValueError, match="at most 200"):
            BannerConfig(width=201)

    def test_invalid_char_raises(self):
        with pytest.raises(ValueError, match="exactly one character"):
            BannerConfig(char="--")

    def test_empty_char_raises(self):
        with pytest.raises(ValueError, match="exactly one character"):
            BannerConfig(char="")

    def test_empty_label_raises(self):
        with pytest.raises(ValueError, match="label must not be empty"):
            BannerConfig(label="   ")

    def test_from_env_defaults(self, monkeypatch):
        for key in ["CRONWRAP_BANNER_ENABLED", "CRONWRAP_BANNER_WIDTH",
                    "CRONWRAP_BANNER_CHAR", "CRONWRAP_BANNER_TIMESTAMP",
                    "CRONWRAP_BANNER_PID", "CRONWRAP_BANNER_LABEL"]:
            monkeypatch.delenv(key, raising=False)
        cfg = BannerConfig.from_env()
        assert cfg.enabled is True
        assert cfg.width == 72

    def test_from_env_disabled(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_BANNER_ENABLED", "false")
        cfg = BannerConfig.from_env()
        assert cfg.enabled is False

    def test_from_env_custom_width(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_BANNER_WIDTH", "80")
        cfg = BannerConfig.from_env()
        assert cfg.width == 80


class TestRenderBanner:
    _NOW = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)

    def test_returns_empty_when_disabled(self):
        cfg = BannerConfig(enabled=False)
        assert render_banner("echo hi", cfg=cfg) == ""

    def test_contains_command(self):
        result = render_banner("echo hello", now=self._NOW)
        assert "echo hello" in result

    def test_contains_timestamp(self):
        result = render_banner("echo hello", now=self._NOW)
        assert "2024-06-01" in result

    def test_no_timestamp_when_disabled(self):
        cfg = BannerConfig(show_timestamp=False)
        result = render_banner("echo hello", cfg=cfg, now=self._NOW)
        assert "2024-06-01" not in result

    def test_contains_pid(self):
        import os
        result = render_banner("echo hello", now=self._NOW)
        assert str(os.getpid()) in result

    def test_no_pid_when_disabled(self):
        import os
        cfg = BannerConfig(show_pid=False)
        result = render_banner("echo hello", cfg=cfg, now=self._NOW)
        assert str(os.getpid()) not in result

    def test_border_uses_char(self):
        cfg = BannerConfig(char="-")
        result = render_banner("cmd", cfg=cfg, now=self._NOW)
        assert "---" in result

    def test_label_in_output(self):
        cfg = BannerConfig(label="myjob")
        result = render_banner("cmd", cfg=cfg, now=self._NOW)
        assert "MYJOB" in result
