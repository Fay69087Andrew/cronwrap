"""Tests for cronwrap.formatter."""
import json
import pytest
from unittest.mock import MagicMock
from cronwrap.formatter import FormatterConfig, format_result


def _result(command="echo hi", exit_code=0, stdout="hi\n", stderr=""):
    r = MagicMock()
    r.command = command
    r.exit_code = exit_code
    r.success = exit_code == 0
    r.stdout = stdout
    r.stderr = stderr
    return r


class TestFormatterConfig:
    def test_defaults(self):
        cfg = FormatterConfig()
        assert cfg.format == "text"
        assert cfg.show_timestamps is True
        assert cfg.show_command is True
        assert cfg.indent == 2
        assert cfg.color is False

    def test_format_lowercased(self):
        cfg = FormatterConfig(format="JSON")
        assert cfg.format == "json"

    def test_invalid_format_raises(self):
        with pytest.raises(ValueError, match="format must be one of"):
            FormatterConfig(format="xml")

    def test_negative_indent_raises(self):
        with pytest.raises(ValueError, match="indent must be >= 0"):
            FormatterConfig(indent=-1)

    def test_large_indent_raises(self):
        with pytest.raises(ValueError, match="indent must be <= 8"):
            FormatterConfig(indent=9)

    def test_from_env_defaults(self, monkeypatch):
        for k in ("CRONWRAP_FORMAT", "CRONWRAP_FORMAT_TIMESTAMPS",
                  "CRONWRAP_FORMAT_COMMAND", "CRONWRAP_FORMAT_INDENT", "CRONWRAP_FORMAT_COLOR"):
            monkeypatch.delenv(k, raising=False)
        cfg = FormatterConfig.from_env()
        assert cfg.format == "text"
        assert cfg.indent == 2

    def test_from_env_custom(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_FORMAT", "compact")
        monkeypatch.setenv("CRONWRAP_FORMAT_COLOR", "true")
        cfg = FormatterConfig.from_env()
        assert cfg.format == "compact"
        assert cfg.color is True


class TestFormatResult:
    def test_text_ok(self):
        cfg = FormatterConfig(format="text")
        out = format_result(cfg, _result())
        assert "OK" in out
        assert "echo hi" in out

    def test_text_fail(self):
        cfg = FormatterConfig(format="text")
        out = format_result(cfg, _result(exit_code=1))
        assert "FAIL" in out

    def test_json_format(self):
        cfg = FormatterConfig(format="json")
        out = format_result(cfg, _result(), timestamp="2024-01-01T00:00:00")
        data = json.loads(out)
        assert data["status"] == "OK"
        assert data["exit_code"] == 0
        assert "timestamp" in data

    def test_compact_format(self):
        cfg = FormatterConfig(format="compact")
        out = format_result(cfg, _result(exit_code=2))
        assert out.startswith("[FAIL]")
        assert "exit=2" in out

    def test_no_command_when_disabled(self):
        cfg = FormatterConfig(show_command=False)
        out = format_result(cfg, _result())
        assert "echo hi" not in out

    def test_no_timestamp_when_disabled(self):
        cfg = FormatterConfig(show_timestamps=False)
        out = format_result(cfg, _result(), timestamp="2024-01-01T00:00:00")
        assert "2024-01-01" not in out
