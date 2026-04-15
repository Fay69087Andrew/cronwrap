"""Tests for cronwrap.dependency."""
from __future__ import annotations

import pytest

from cronwrap.dependency import (
    DependencyConfig,
    DependencyResult,
    all_passed,
    check_all,
    run_dependency_check,
)


# ---------------------------------------------------------------------------
# DependencyConfig
# ---------------------------------------------------------------------------

class TestDependencyConfig:
    def test_defaults(self):
        cfg = DependencyConfig()
        assert cfg.checks == []
        assert cfg.timeout_seconds == 10
        assert cfg.enabled is True

    def test_zero_timeout_raises(self):
        with pytest.raises(ValueError, match="positive"):
            DependencyConfig(timeout_seconds=0)

    def test_negative_timeout_raises(self):
        with pytest.raises(ValueError, match="positive"):
            DependencyConfig(timeout_seconds=-5)

    def test_from_env_defaults(self, monkeypatch):
        monkeypatch.delenv("CRONWRAP_DEP_CHECKS", raising=False)
        monkeypatch.delenv("CRONWRAP_DEP_TIMEOUT", raising=False)
        monkeypatch.delenv("CRONWRAP_DEP_ENABLED", raising=False)
        cfg = DependencyConfig.from_env()
        assert cfg.checks == []
        assert cfg.timeout_seconds == 10
        assert cfg.enabled is True

    def test_from_env_custom(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_DEP_CHECKS", "echo ok, true")
        monkeypatch.setenv("CRONWRAP_DEP_TIMEOUT", "5")
        monkeypatch.setenv("CRONWRAP_DEP_ENABLED", "false")
        cfg = DependencyConfig.from_env()
        assert cfg.checks == ["echo ok", "true"]
        assert cfg.timeout_seconds == 5
        assert cfg.enabled is False


# ---------------------------------------------------------------------------
# DependencyResult
# ---------------------------------------------------------------------------

class TestDependencyResult:
    def test_passed_on_zero_exit(self):
        r = DependencyResult(command="true", exit_code=0, stdout="", stderr="")
        assert r.passed is True

    def test_failed_on_nonzero_exit(self):
        r = DependencyResult(command="false", exit_code=1, stdout="", stderr="")
        assert r.passed is False


# ---------------------------------------------------------------------------
# run_dependency_check
# ---------------------------------------------------------------------------

class TestRunDependencyCheck:
    def test_passing_command(self):
        r = run_dependency_check("true", timeout=5)
        assert r.passed
        assert r.command == "true"

    def test_failing_command(self):
        r = run_dependency_check("false", timeout=5)
        assert not r.passed

    def test_timeout_returns_failure(self):
        r = run_dependency_check("sleep 10", timeout=1)
        assert not r.passed
        assert "Timed out" in r.stderr


# ---------------------------------------------------------------------------
# check_all / all_passed
# ---------------------------------------------------------------------------

class TestCheckAll:
    def test_disabled_returns_empty(self):
        cfg = DependencyConfig(checks=["false"], enabled=False)
        assert check_all(cfg) == []

    def test_all_pass(self):
        cfg = DependencyConfig(checks=["true", "echo hi"])
        results = check_all(cfg)
        assert all_passed(results)

    def test_one_fails(self):
        cfg = DependencyConfig(checks=["true", "false"])
        results = check_all(cfg)
        assert not all_passed(results)

    def test_empty_results_all_passed(self):
        assert all_passed([]) is True
