"""Tests for cronwrap.prefix_integration."""
import pytest
from cronwrap.prefix import PrefixConfig
from cronwrap.prefix_integration import (
    apply_prefix_to_output,
    apply_prefix_to_result,
    report_prefix,
    build_prefix_config,
)


class _FakeResult:
    def __init__(self, stdout="", stderr="", exit_code=0, command="echo hi"):
        self.stdout = stdout
        self.stderr = stderr
        self.exit_code = exit_code
        self.command = command


class TestApplyPrefixToOutput:
    def test_prefixes_stdout_and_stderr(self):
        cfg = PrefixConfig(job_name="myjob")
        out, err = apply_prefix_to_output("hello", "oops", cfg)
        assert out == "[myjob] hello"
        assert err == "[myjob] oops"

    def test_disabled_leaves_output_unchanged(self):
        cfg = PrefixConfig(enabled=False)
        out, err = apply_prefix_to_output("a", "b", cfg)
        assert out == "a"
        assert err == "b"


class TestApplyPrefixToResult:
    def test_returns_dict_with_prefixed_output(self):
        cfg = PrefixConfig(job_name="job1")
        r = _FakeResult(stdout="line1", stderr="err1", exit_code=0)
        d = apply_prefix_to_result(r, cfg)
        assert d["stdout"] == "[job1] line1"
        assert d["stderr"] == "[job1] err1"
        assert d["exit_code"] == 0

    def test_bytes_stdout_decoded(self):
        cfg = PrefixConfig(job_name="j")
        r = _FakeResult(stdout=b"bytes output", stderr=b"")
        d = apply_prefix_to_result(r, cfg)
        assert "bytes output" in d["stdout"]

    def test_none_stdout_treated_as_empty(self):
        cfg = PrefixConfig(job_name="j")
        r = _FakeResult(stdout=None, stderr=None)
        d = apply_prefix_to_result(r, cfg)
        assert d["stdout"] == ""
        assert d["stderr"] == ""


class TestReportPrefix:
    def test_enabled_report(self):
        cfg = PrefixConfig(job_name="myj", enabled=True)
        s = report_prefix(cfg)
        assert "enabled" in s
        assert "myj" in s

    def test_disabled_report(self):
        cfg = PrefixConfig(enabled=False)
        s = report_prefix(cfg)
        assert "disabled" in s


def test_build_prefix_config_returns_config(monkeypatch):
    monkeypatch.delenv("CRONWRAP_PREFIX_ENABLED", raising=False)
    cfg = build_prefix_config()
    assert isinstance(cfg, PrefixConfig)
