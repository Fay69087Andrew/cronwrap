"""Tests for cronwrap.circuit_breaker_integration."""

import pytest

from cronwrap.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from cronwrap.circuit_breaker_integration import (
    build_circuit_breaker,
    check_circuit_or_abort,
    circuit_summary,
    update_circuit_from_result,
)
from cronwrap.runner import RunResult


def _make_result(exit_code: int) -> RunResult:
    return RunResult(command="echo hi", exit_code=exit_code, stdout=b"", stderr=b"")


def _cb(tmp_path, threshold=2):
    cfg = CircuitBreakerConfig(
        enabled=True,
        failure_threshold=threshold,
        recovery_timeout=300,
        state_dir=str(tmp_path),
    )
    return CircuitBreaker("myjob", cfg)


class TestCheckCircuitOrAbort:
    def test_does_not_raise_when_closed(self, tmp_path):
        cb = _cb(tmp_path)
        check_circuit_or_abort(cb)  # should not raise

    def test_raises_system_exit_when_open(self, tmp_path):
        cb = _cb(tmp_path, threshold=1)
        cb.record_failure()
        with pytest.raises(SystemExit, match="Circuit breaker OPEN"):
            check_circuit_or_abort(cb)

    def test_exit_message_includes_job_name(self, tmp_path):
        cb = _cb(tmp_path, threshold=1)
        cb.record_failure()
        with pytest.raises(SystemExit) as exc_info:
            check_circuit_or_abort(cb)
        assert "myjob" in str(exc_info.value)


class TestUpdateCircuitFromResult:
    def test_success_resets_failures(self, tmp_path):
        cb = _cb(tmp_path, threshold=5)
        cb.record_failure()
        update_circuit_from_result(cb, _make_result(0))
        assert cb.current_state().consecutive_failures == 0

    def test_failure_increments_counter(self, tmp_path):
        cb = _cb(tmp_path)
        update_circuit_from_result(cb, _make_result(1))
        assert cb.current_state().consecutive_failures == 1

    def test_repeated_failure_opens_circuit(self, tmp_path):
        cb = _cb(tmp_path, threshold=2)
        update_circuit_from_result(cb, _make_result(1))
        update_circuit_from_result(cb, _make_result(1))
        assert cb.current_state().status == "open"


class TestCircuitSummary:
    def test_contains_job_name(self, tmp_path):
        cb = _cb(tmp_path)
        assert "myjob" in circuit_summary(cb)

    def test_contains_status(self, tmp_path):
        cb = _cb(tmp_path)
        assert "closed" in circuit_summary(cb)

    def test_shows_open_duration_when_open(self, tmp_path):
        cb = _cb(tmp_path, threshold=1)
        cb.record_failure()
        summary = circuit_summary(cb)
        assert "open for" in summary


class TestBuildCircuitBreaker:
    def test_returns_circuit_breaker_instance(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CRONWRAP_CB_STATE_DIR", str(tmp_path))
        cb = build_circuit_breaker("somejob")
        assert isinstance(cb, CircuitBreaker)
        assert cb.job_name == "somejob"

    def test_uses_supplied_config(self, tmp_path):
        cfg = CircuitBreakerConfig(state_dir=str(tmp_path))
        cb = build_circuit_breaker("x", config=cfg)
        assert cb.config is cfg
