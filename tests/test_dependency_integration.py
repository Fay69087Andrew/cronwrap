"""Tests for cronwrap.dependency_integration."""
from __future__ import annotations

import pytest

from cronwrap.dependency import DependencyConfig, DependencyResult
from cronwrap.dependency_integration import (
    dependency_summary,
    run_dependency_checks_or_abort,
)


def _ok(cmd: str = "true") -> DependencyResult:
    return DependencyResult(command=cmd, exit_code=0, stdout="", stderr="")


def _fail(cmd: str = "false", stderr: str = "err") -> DependencyResult:
    return DependencyResult(command=cmd, exit_code=1, stdout="", stderr=stderr)


class TestRunDependencyChecksOrAbort:
    def test_does_not_raise_when_all_pass(self):
        cfg = DependencyConfig(checks=["true"])
        results = run_dependency_checks_or_abort(cfg)
        assert all(r.passed for r in results)

    def test_raises_system_exit_on_failure(self):
        cfg = DependencyConfig(checks=["false"])
        with pytest.raises(SystemExit) as exc_info:
            run_dependency_checks_or_abort(cfg)
        assert exc_info.value.code == 1

    def test_disabled_returns_empty_without_abort(self):
        cfg = DependencyConfig(checks=["false"], enabled=False)
        results = run_dependency_checks_or_abort(cfg)
        assert results == []

    def test_prints_failed_commands_to_stderr(self, capsys):
        cfg = DependencyConfig(checks=["false"])
        with pytest.raises(SystemExit):
            run_dependency_checks_or_abort(cfg)
        captured = capsys.readouterr()
        assert "false" in captured.err


class TestDependencySummary:
    def test_empty_results(self):
        assert dependency_summary([]) == "dependency_checks: none"

    def test_all_passed(self):
        summary = dependency_summary([_ok("echo hi"), _ok("true")])
        assert "2/2 passed" in summary
        assert "[OK]" in summary

    def test_partial_failure(self):
        summary = dependency_summary([_ok("true"), _fail("false")])
        assert "1/2 passed" in summary
        assert "[FAIL]" in summary
        assert "[OK]" in summary

    def test_all_failed(self):
        summary = dependency_summary([_fail("false"), _fail("exit 2")])
        assert "0/2 passed" in summary
