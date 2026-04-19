"""Tests for cronwrap.trimmer and cronwrap.trimmer_integration."""
from __future__ import annotations

import pytest

from cronwrap.trimmer import TrimmerConfig, trim_output, trimmer_summary
from cronwrap.trimmer_integration import trim_result_output, apply_trimmer


class TestTrimmerConfig:
    def test_defaults(self):
        cfg = TrimmerConfig()
        assert cfg.enabled is True
        assert cfg.strip_leading_blank_lines is True
        assert cfg.strip_trailing_blank_lines is True
        assert cfg.collapse_blank_lines is False
        assert cfg.max_consecutive_blank == 1

    def test_zero_max_consecutive_raises(self):
        with pytest.raises(ValueError):
            TrimmerConfig(max_consecutive_blank=0)

    def test_negative_max_consecutive_raises(self):
        with pytest.raises(ValueError):
            TrimmerConfig(max_consecutive_blank=-1)

    def test_invalid_enabled_type_raises(self):
        with pytest.raises(TypeError):
            TrimmerConfig(enabled="yes")  # type: ignore

    def test_from_env_defaults(self, monkeypatch):
        for key in [
            "CRONWRAP_TRIMMER_ENABLED",
            "CRONWRAP_TRIMMER_STRIP_LEADING",
            "CRONWRAP_TRIMMER_STRIP_TRAILING",
            "CRONWRAP_TRIMMER_COLLAPSE_BLANK",
            "CRONWRAP_TRIMMER_MAX_CONSECUTIVE_BLANK",
        ]:
            monkeypatch.delenv(key, raising=False)
        cfg = TrimmerConfig.from_env()
        assert cfg.enabled is True
        assert cfg.collapse_blank_lines is False
        assert cfg.max_consecutive_blank == 1

    def test_from_env_custom(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_TRIMMER_ENABLED", "false")
        monkeypatch.setenv("CRONWRAP_TRIMMER_COLLAPSE_BLANK", "true")
        monkeypatch.setenv("CRONWRAP_TRIMMER_MAX_CONSECUTIVE_BLANK", "3")
        cfg = TrimmerConfig.from_env()
        assert cfg.enabled is False
        assert cfg.collapse_blank_lines is True
        assert cfg.max_consecutive_blank == 3


class TestTrimOutput:
    def test_strips_leading_blank_lines(self):
        result = trim_output("\n\nhello")
        assert result == "hello"

    def test_strips_trailing_blank_lines(self):
        result = trim_output("hello\n\n")
        assert result == "hello"

    def test_does_not_strip_when_disabled(self):
        cfg = TrimmerConfig(enabled=False)
        text = "\nhello\n"
        assert trim_output(text, cfg) == text

    def test_collapses_blank_lines(self):
        cfg = TrimmerConfig(collapse_blank_lines=True, max_consecutive_blank=1)
        text = "a\n\n\nb"
        result = trim_output(text, cfg)
        assert result == "a\n\nb"

    def test_collapse_allows_two_consecutive(self):
        cfg = TrimmerConfig(collapse_blank_lines=True, max_consecutive_blank=2)
        text = "a\n\n\n\nb"
        result = trim_output(text, cfg)
        assert result == "a\n\n\nb"

    def test_empty_string_unchanged(self):
        assert trim_output("") == ""

    def test_none_config_uses_defaults(self):
        result = trim_output("\nhello\n", None)
        assert result == "hello"


class TestTrimmerSummary:
    def test_keys_present(self):
        cfg = TrimmerConfig()
        s = trimmer_summary(cfg)
        assert set(s.keys()) == {
            "enabled",
            "strip_leading_blank_lines",
            "strip_trailing_blank_lines",
            "collapse_blank_lines",
            "max_consecutive_blank",
        }


class TestTrimResultOutput:
    def test_trims_both_streams(self):
        cfg = TrimmerConfig()
        out, err = trim_result_output("\nhello\n", "\nworld\n", cfg)
        assert out == "hello"
        assert err == "world"

    def test_apply_trimmer_returns_dict_with_streams(self, monkeypatch):
        monkeypatch.delenv("CRONWRAP_TRIMMER_ENABLED", raising=False)
        summary = apply_trimmer("\nout\n", "\nerr\n")
        assert summary["stdout"] == "out"
        assert summary["stderr"] == "err"
        assert "enabled" in summary
