"""Tests for cronwrap.circuit_breaker."""

import json
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from cronwrap.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
)


# ---------------------------------------------------------------------------
# CircuitBreakerConfig
# ---------------------------------------------------------------------------

class TestCircuitBreakerConfig:
    def test_defaults(self):
        cfg = CircuitBreakerConfig()
        assert cfg.enabled is False
        assert cfg.failure_threshold == 3
        assert cfg.recovery_timeout == 300
        assert cfg.state_dir == "/tmp/cronwrap/circuit"

    def test_zero_failure_threshold_raises(self):
        with pytest.raises(ValueError, match="failure_threshold"):
            CircuitBreakerConfig(failure_threshold=0)

    def test_zero_recovery_timeout_raises(self):
        with pytest.raises(ValueError, match="recovery_timeout"):
            CircuitBreakerConfig(recovery_timeout=0)

    def test_empty_state_dir_raises(self):
        with pytest.raises(ValueError, match="state_dir"):
            CircuitBreakerConfig(state_dir="")

    def test_from_env_defaults(self, monkeypatch):
        for k in ("CRONWRAP_CB_ENABLED", "CRONWRAP_CB_FAILURE_THRESHOLD",
                  "CRONWRAP_CB_RECOVERY_TIMEOUT", "CRONWRAP_CB_STATE_DIR"):
            monkeypatch.delenv(k, raising=False)
        cfg = CircuitBreakerConfig.from_env()
        assert cfg.enabled is False
        assert cfg.failure_threshold == 3

    def test_from_env_custom(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_CB_ENABLED", "true")
        monkeypatch.setenv("CRONWRAP_CB_FAILURE_THRESHOLD", "5")
        monkeypatch.setenv("CRONWRAP_CB_RECOVERY_TIMEOUT", "60")
        cfg = CircuitBreakerConfig.from_env()
        assert cfg.enabled is True
        assert cfg.failure_threshold == 5
        assert cfg.recovery_timeout == 60


# ---------------------------------------------------------------------------
# CircuitState
# ---------------------------------------------------------------------------

class TestCircuitState:
    def test_defaults(self):
        s = CircuitState()
        assert s.status == "closed"
        assert s.consecutive_failures == 0
        assert s.opened_at is None

    def test_roundtrip(self):
        s = CircuitState(status="open", consecutive_failures=2, opened_at=1234.5)
        assert CircuitState.from_dict(s.to_dict()).status == "open"
        assert CircuitState.from_dict(s.to_dict()).consecutive_failures == 2


# ---------------------------------------------------------------------------
# CircuitBreaker
# ---------------------------------------------------------------------------

def _cb(tmp_path, threshold=2, recovery=60):
    cfg = CircuitBreakerConfig(
        enabled=True,
        failure_threshold=threshold,
        recovery_timeout=recovery,
        state_dir=str(tmp_path),
    )
    return CircuitBreaker("test_job", cfg)


class TestCircuitBreaker:
    def test_initially_closed(self, tmp_path):
        cb = _cb(tmp_path)
        assert cb.is_open() is False

    def test_opens_after_threshold(self, tmp_path):
        cb = _cb(tmp_path, threshold=2)
        cb.record_failure()
        assert cb.is_open() is False
        cb.record_failure()
        assert cb.is_open() is True

    def test_success_resets_circuit(self, tmp_path):
        cb = _cb(tmp_path, threshold=2)
        cb.record_failure()
        cb.record_failure()
        assert cb.is_open() is True
        cb.record_success()
        assert cb.is_open() is False
        assert cb.current_state().consecutive_failures == 0

    def test_half_open_after_recovery_timeout(self, tmp_path):
        cb = _cb(tmp_path, threshold=1, recovery=10)
        cb.record_failure()
        assert cb.is_open() is True
        # Simulate time passing beyond recovery_timeout
        state = cb.current_state()
        state.opened_at = time.time() - 20
        cb._save(state)
        assert cb.is_open() is False  # moved to half-open
        assert cb.current_state().status == "half-open"

    def test_state_persisted_to_disk(self, tmp_path):
        cb = _cb(tmp_path, threshold=2)
        cb.record_failure()
        data = json.loads((tmp_path / "test_job.json").read_text())
        assert data["consecutive_failures"] == 1
