"""Tests for cronwrap.output_capture."""
from __future__ import annotations

import pytest

from cronwrap.output_capture import (
    CapturedOutput,
    OutputCaptureConfig,
    decode_output,
)


# ---------------------------------------------------------------------------
# OutputCaptureConfig
# ---------------------------------------------------------------------------

class TestOutputCaptureConfig:
    def test_defaults(self):
        cfg = OutputCaptureConfig()
        assert cfg.max_bytes == 1024 * 1024
        assert cfg.encoding == "utf-8"
        assert cfg.capture_stdout is True
        assert cfg.capture_stderr is True

    def test_zero_max_bytes_raises(self):
        with pytest.raises(ValueError, match="max_bytes must be positive"):
            OutputCaptureConfig(max_bytes=0)

    def test_negative_max_bytes_raises(self):
        with pytest.raises(ValueError, match="max_bytes must be positive"):
            OutputCaptureConfig(max_bytes=-1)

    def test_empty_encoding_raises(self):
        with pytest.raises(ValueError, match="encoding must not be empty"):
            OutputCaptureConfig(encoding="")

    def test_from_env_defaults(self, monkeypatch):
        for key in ("CRONWRAP_MAX_OUTPUT_BYTES", "CRONWRAP_OUTPUT_ENCODING",
                    "CRONWRAP_CAPTURE_STDOUT", "CRONWRAP_CAPTURE_STDERR"):
            monkeypatch.delenv(key, raising=False)
        cfg = OutputCaptureConfig.from_env()
        assert cfg.max_bytes == 1024 * 1024
        assert cfg.encoding == "utf-8"
        assert cfg.capture_stdout is True
        assert cfg.capture_stderr is True

    def test_from_env_custom(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_MAX_OUTPUT_BYTES", "2048")
        monkeypatch.setenv("CRONWRAP_OUTPUT_ENCODING", "latin-1")
        monkeypatch.setenv("CRONWRAP_CAPTURE_STDOUT", "false")
        monkeypatch.setenv("CRONWRAP_CAPTURE_STDERR", "true")
        cfg = OutputCaptureConfig.from_env()
        assert cfg.max_bytes == 2048
        assert cfg.encoding == "latin-1"
        assert cfg.capture_stdout is False
        assert cfg.capture_stderr is True


# ---------------------------------------------------------------------------
# CapturedOutput
# ---------------------------------------------------------------------------

class TestCapturedOutput:
    def test_combined_both(self):
        co = CapturedOutput(stdout="hello", stderr="world")
        assert co.combined() == "hello\nworld"

    def test_combined_only_stdout(self):
        co = CapturedOutput(stdout="hello", stderr="")
        assert co.combined() == "hello"

    def test_combined_empty(self):
        co = CapturedOutput()
        assert co.combined() == ""


# ---------------------------------------------------------------------------
# decode_output
# ---------------------------------------------------------------------------

class TestDecodeOutput:
    def test_basic_decode(self):
        cfg = OutputCaptureConfig()
        result = decode_output(b"out", b"err", cfg)
        assert result.stdout == "out"
        assert result.stderr == "err"
        assert result.truncated is False

    def test_truncation_flag_set(self):
        cfg = OutputCaptureConfig(max_bytes=5)
        result = decode_output(b"hello world", b"", cfg)
        assert result.truncated is True

    def test_stdout_truncated_to_max_bytes(self):
        cfg = OutputCaptureConfig(max_bytes=4)
        result = decode_output(b"abcdefgh", b"", cfg)
        assert result.stdout == "abcd"

    def test_capture_stdout_false_omits_stdout(self):
        cfg = OutputCaptureConfig(capture_stdout=False)
        result = decode_output(b"out", b"err", cfg)
        assert result.stdout == ""
        assert result.stderr == "err"

    def test_capture_stderr_false_omits_stderr(self):
        cfg = OutputCaptureConfig(capture_stderr=False)
        result = decode_output(b"out", b"err", cfg)
        assert result.stdout == "out"
        assert result.stderr == ""

    def test_invalid_bytes_replaced(self):
        cfg = OutputCaptureConfig(encoding="utf-8")
        result = decode_output(b"\xff\xfe", b"", cfg)
        assert isinstance(result.stdout, str)
