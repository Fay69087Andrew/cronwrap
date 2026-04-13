"""Tests for cronwrap.truncate."""

from __future__ import annotations

import pytest

from cronwrap.truncate import TruncateConfig, truncate_text, _TRUNCATION_NOTICE


# ---------------------------------------------------------------------------
# TruncateConfig
# ---------------------------------------------------------------------------

class TestTruncateConfig:
    def test_defaults(self):
        cfg = TruncateConfig()
        assert cfg.max_bytes == 64 * 1024
        assert cfg.max_lines == 1000
        assert cfg.enabled is True

    def test_zero_max_bytes_raises(self):
        with pytest.raises(ValueError, match="max_bytes"):
            TruncateConfig(max_bytes=0)

    def test_negative_max_bytes_raises(self):
        with pytest.raises(ValueError, match="max_bytes"):
            TruncateConfig(max_bytes=-1)

    def test_zero_max_lines_raises(self):
        with pytest.raises(ValueError, match="max_lines"):
            TruncateConfig(max_lines=0)

    def test_negative_max_lines_raises(self):
        with pytest.raises(ValueError, match="max_lines"):
            TruncateConfig(max_lines=-5)

    def test_from_env_defaults(self, monkeypatch):
        for key in ("CRONWRAP_TRUNCATE_ENABLED", "CRONWRAP_TRUNCATE_MAX_BYTES", "CRONWRAP_TRUNCATE_MAX_LINES"):
            monkeypatch.delenv(key, raising=False)
        cfg = TruncateConfig.from_env()
        assert cfg.enabled is True
        assert cfg.max_bytes == 64 * 1024
        assert cfg.max_lines == 1000

    def test_from_env_disabled(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_TRUNCATE_ENABLED", "false")
        cfg = TruncateConfig.from_env()
        assert cfg.enabled is False

    def test_from_env_custom_values(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_TRUNCATE_MAX_BYTES", "1024")
        monkeypatch.setenv("CRONWRAP_TRUNCATE_MAX_LINES", "50")
        cfg = TruncateConfig.from_env()
        assert cfg.max_bytes == 1024
        assert cfg.max_lines == 50


# ---------------------------------------------------------------------------
# truncate_text
# ---------------------------------------------------------------------------

class TestTruncateText:
    def _cfg(self, **kwargs) -> TruncateConfig:
        return TruncateConfig(**kwargs)

    def test_short_text_unchanged(self):
        cfg = self._cfg(max_bytes=1024, max_lines=100)
        text = "hello world\n"
        assert truncate_text(text, cfg) == text

    def test_empty_text_unchanged(self):
        cfg = self._cfg()
        assert truncate_text("", cfg) == ""

    def test_disabled_returns_original(self):
        cfg = self._cfg(max_bytes=5, max_lines=1, enabled=False)
        long_text = "a\nb\nc\nd\n"
        assert truncate_text(long_text, cfg) == long_text

    def test_line_limit_truncates(self):
        cfg = self._cfg(max_bytes=10_000, max_lines=3)
        text = "\n".join(str(i) for i in range(10)) + "\n"
        result = truncate_text(text, cfg)
        lines = result.split("\n")
        # first 3 content lines + truncation notice
        assert lines[0] == "0"
        assert lines[1] == "1"
        assert lines[2] == "2"
        assert _TRUNCATION_NOTICE.strip() in result

    def test_byte_limit_truncates(self):
        cfg = self._cfg(max_bytes=10, max_lines=10_000)
        text = "a" * 100
        result = truncate_text(text, cfg)
        assert len(result.encode("utf-8")) > 0
        assert _TRUNCATION_NOTICE.strip() in result

    def test_truncation_notice_appended_once(self):
        cfg = self._cfg(max_bytes=10_000, max_lines=2)
        text = "line1\nline2\nline3\n"
        result = truncate_text(text, cfg)
        assert result.count(_TRUNCATION_NOTICE.strip()) == 1
