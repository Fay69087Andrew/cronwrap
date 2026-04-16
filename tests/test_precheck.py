"""Tests for cronwrap.precheck."""
from __future__ import annotations

import pytest

from cronwrap.precheck import (
    PrecheckConfig,
    PrecheckResult,
    precheck_summary,
    run_prechecks,
)


# ---------------------------------------------------------------------------
# TestPrecheckConfig
# ---------------------------------------------------------------------------

class TestPrecheckConfig:
    def test_defaults(self):
        cfg = PrecheckConfig()
        assert cfg.enabled is True
        assert cfg.abort_on_failure is True
        assert cfg.checks == []

    def test_checks_stripped_and_lowercased(self):
        cfg = PrecheckConfig(checks=[" Disk_Space ", "TMP_WRITABLE"])
        assert cfg.checks == ["disk_space", "tmp_writable"]

    def test_empty_check_names_filtered(self):
        cfg = PrecheckConfig(checks=["", "  ", "disk_space"])
        assert cfg.checks == ["disk_space"]

    def test_from_env_defaults(self, monkeypatch):
        for key in (
            "CRONWRAP_PRECHECK_ENABLED",
            "CRONWRAP_PRECHECK_ABORT_ON_FAILURE",
            "CRONWRAP_PRECHECK_CHECKS",
        ):
            monkeypatch.delenv(key, raising=False)
        cfg = PrecheckConfig.from_env()
        assert cfg.enabled is True
        assert cfg.abort_on_failure is True
        assert cfg.checks == []

    def test_from_env_disabled(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_PRECHECK_ENABLED", "false")
        monkeypatch.delenv("CRONWRAP_PRECHECK_ABORT_ON_FAILURE", raising=False)
        monkeypatch.delenv("CRONWRAP_PRECHECK_CHECKS", raising=False)
        cfg = PrecheckConfig.from_env()
        assert cfg.enabled is False

    def test_from_env_checks_parsed(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_PRECHECK_CHECKS", "disk_space,tmp_writable")
        monkeypatch.delenv("CRONWRAP_PRECHECK_ENABLED", raising=False)
        monkeypatch.delenv("CRONWRAP_PRECHECK_ABORT_ON_FAILURE", raising=False)
        cfg = PrecheckConfig.from_env()
        assert cfg.checks == ["disk_space", "tmp_writable"]


# ---------------------------------------------------------------------------
# TestPrecheckResult
# ---------------------------------------------------------------------------

class TestPrecheckResult:
    def test_str_pass(self):
        r = PrecheckResult("my_check", True, "all good")
        assert str(r) == "[PASS] my_check — all good"

    def test_str_fail(self):
        r = PrecheckResult("my_check", False, "something wrong")
        assert str(r) == "[FAIL] my_check — something wrong"

    def test_str_no_message(self):
        r = PrecheckResult("my_check", True)
        assert str(r) == "[PASS] my_check"


# ---------------------------------------------------------------------------
# TestRunPrechecks
# ---------------------------------------------------------------------------

def _pass_check() -> PrecheckResult:
    return PrecheckResult("custom_pass", True, "ok")


def _fail_check() -> PrecheckResult:
    return PrecheckResult("custom_fail", False, "nope")


class TestRunPrechecks:
    def test_returns_empty_when_disabled(self):
        cfg = PrecheckConfig(enabled=False, checks=["disk_space"])
        assert run_prechecks(cfg) == []

    def test_extra_checks_run(self):
        cfg = PrecheckConfig(checks=[])
        results = run_prechecks(cfg, extra=[_pass_check])
        assert len(results) == 1
        assert results[0].name == "custom_pass"
        assert results[0].passed is True

    def test_unknown_builtin_fails(self):
        cfg = PrecheckConfig(checks=["nonexistent_check"])
        results = run_prechecks(cfg)
        assert len(results) == 1
        assert results[0].passed is False
        assert "unknown" in results[0].message

    def test_mixed_extra_results(self):
        cfg = PrecheckConfig(checks=[])
        results = run_prechecks(cfg, extra=[_pass_check, _fail_check])
        assert results[0].passed is True
        assert results[1].passed is False

    def test_builtin_tmp_writable_runs(self):
        cfg = PrecheckConfig(checks=["tmp_writable"])
        results = run_prechecks(cfg)
        assert len(results) == 1
        assert results[0].name == "tmp_writable"
        # On any normal CI machine /tmp should be writable
        assert results[0].passed is True


# ---------------------------------------------------------------------------
# TestPrecheckSummary
# ---------------------------------------------------------------------------

class TestPrecheckSummary:
    def test_empty_results(self):
        assert precheck_summary([]) == "No pre-flight checks ran."

    def test_all_pass(self):
        results = [PrecheckResult("a", True), PrecheckResult("b", True)]
        summary = precheck_summary(results)
        assert "2 check(s), 0 failed" in summary

    def test_some_fail(self):
        results = [PrecheckResult("a", True), PrecheckResult("b", False)]
        summary = precheck_summary(results)
        assert "2 check(s), 1 failed" in summary
        assert "[FAIL] b" in summary
