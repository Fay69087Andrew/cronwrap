"""Tests for cronwrap.output_capture_integration."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from cronwrap.output_capture import CapturedOutput, OutputCaptureConfig
from cronwrap.output_capture_integration import capture_from_result, output_summary


def _make_result(stdout: bytes = b"", stderr: bytes = b"", exit_code: int = 0):
    result = MagicMock()
    result.stdout = stdout
    result.stderr = stderr
    result.exit_code = exit_code
    return result


class TestCaptureFromResult:
    def test_decodes_stdout(self):
        result = _make_result(stdout=b"hello")
        cfg = OutputCaptureConfig()
        captured = capture_from_result(result, config=cfg)
        assert captured.stdout == "hello"

    def test_decodes_stderr(self):
        result = _make_result(stderr=b"oops")
        cfg = OutputCaptureConfig()
        captured = capture_from_result(result, config=cfg)
        assert captured.stderr == "oops"

    def test_non_bytes_stdout_treated_as_empty(self):
        result = _make_result()
        result.stdout = None  # simulate missing attribute
        cfg = OutputCaptureConfig()
        captured = capture_from_result(result, config=cfg)
        assert captured.stdout == ""

    def test_uses_env_config_when_none_given(self, monkeypatch):
        for key in ("CRONWRAP_MAX_OUTPUT_BYTES", "CRONWRAP_OUTPUT_ENCODING",
                    "CRONWRAP_CAPTURE_STDOUT", "CRONWRAP_CAPTURE_STDERR"):
            monkeypatch.delenv(key, raising=False)
        result = _make_result(stdout=b"env-default")
        captured = capture_from_result(result)
        assert captured.stdout == "env-default"

    def test_truncation_propagated(self):
        result = _make_result(stdout=b"abcdef")
        cfg = OutputCaptureConfig(max_bytes=3)
        captured = capture_from_result(result, config=cfg)
        assert captured.truncated is True


class TestOutputSummary:
    def test_no_output_returns_placeholder(self):
        co = CapturedOutput()
        assert output_summary(co) == "(no output)"

    def test_short_output_returned_as_is(self):
        co = CapturedOutput(stdout="hello")
        assert output_summary(co) == "hello"

    def test_long_output_truncated_with_suffix(self):
        co = CapturedOutput(stdout="x" * 600)
        summary = output_summary(co, max_chars=500)
        assert len(summary) > 500
        assert summary.endswith(" ... [truncated]")
        assert summary.startswith("x" * 500)

    def test_truncated_flag_adds_suffix(self):
        co = CapturedOutput(stdout="short", truncated=True)
        summary = output_summary(co, max_chars=500)
        assert "[truncated]" in summary

    def test_zero_max_chars_raises(self):
        co = CapturedOutput(stdout="hi")
        with pytest.raises(ValueError, match="max_chars must be positive"):
            output_summary(co, max_chars=0)

    def test_combined_stdout_and_stderr(self):
        co = CapturedOutput(stdout="out", stderr="err")
        summary = output_summary(co)
        assert "out" in summary
        assert "err" in summary
