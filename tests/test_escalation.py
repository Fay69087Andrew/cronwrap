"""Tests for cronwrap.escalation."""
import json
import time
from pathlib import Path

import pytest

from cronwrap.escalation import (
    EscalationConfig,
    EscalationState,
    evaluate_escalation,
    escalation_summary,
    load_state,
    save_state,
)


class TestEscalationConfig:
    def test_defaults(self):
        cfg = EscalationConfig()
        assert cfg.enabled is False
        assert cfg.threshold == 3
        assert cfg.interval == 3600

    def test_zero_threshold_raises(self):
        with pytest.raises(ValueError, match="threshold"):
            EscalationConfig(threshold=0)

    def test_negative_interval_raises(self):
        with pytest.raises(ValueError, match="interval"):
            EscalationConfig(interval=-1)

    def test_empty_state_dir_raises(self):
        with pytest.raises(ValueError, match="state_dir"):
            EscalationConfig(state_dir="")

    def test_from_env_defaults(self, monkeypatch):
        for k in ["CRONWRAP_ESCALATION_ENABLED", "CRONWRAP_ESCALATION_THRESHOLD",
                  "CRONWRAP_ESCALATION_INTERVAL", "CRONWRAP_ESCALATION_STATE_DIR"]:
            monkeypatch.delenv(k, raising=False)
        cfg = EscalationConfig.from_env()
        assert cfg.enabled is False
        assert cfg.threshold == 3

    def test_from_env_custom(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_ESCALATION_ENABLED", "true")
        monkeypatch.setenv("CRONWRAP_ESCALATION_THRESHOLD", "5")
        cfg = EscalationConfig.from_env()
        assert cfg.enabled is True
        assert cfg.threshold == 5


class TestEscalationState:
    def test_roundtrip(self):
        s = EscalationState(consecutive_failures=2, last_escalated_at=1234.5)
        assert EscalationState.from_dict(s.to_dict()).consecutive_failures == 2

    def test_defaults_from_empty_dict(self):
        s = EscalationState.from_dict({})
        assert s.consecutive_failures == 0
        assert s.last_escalated_at is None


class TestEvaluateEscalation:
    def _cfg(self, tmp_path, threshold=3, interval=60):
        return EscalationConfig(enabled=True, threshold=threshold, interval=interval,
                                state_dir=str(tmp_path))

    def test_disabled_always_false(self, tmp_path):
        cfg = EscalationConfig(enabled=False, state_dir=str(tmp_path))
        for _ in range(10):
            assert evaluate_escalation(cfg, "job", False) is False

    def test_success_resets_and_returns_false(self, tmp_path):
        cfg = self._cfg(tmp_path)
        evaluate_escalation(cfg, "job", False, now=1000.0)
        evaluate_escalation(cfg, "job", False, now=1001.0)
        evaluate_escalation(cfg, "job", True, now=1002.0)
        state = load_state(cfg, "job")
        assert state.consecutive_failures == 0

    def test_escalates_at_threshold(self, tmp_path):
        cfg = self._cfg(tmp_path, threshold=2)
        assert evaluate_escalation(cfg, "job", False, now=1000.0) is False
        assert evaluate_escalation(cfg, "job", False, now=1001.0) is True

    def test_no_repeat_within_interval(self, tmp_path):
        cfg = self._cfg(tmp_path, threshold=2, interval=300)
        evaluate_escalation(cfg, "job", False, now=1000.0)
        evaluate_escalation(cfg, "job", False, now=1001.0)  # escalates
        result = evaluate_escalation(cfg, "job", False, now=1100.0)  # within interval
        assert result is False

    def test_re_escalates_after_interval(self, tmp_path):
        cfg = self._cfg(tmp_path, threshold=2, interval=300)
        evaluate_escalation(cfg, "job", False, now=1000.0)
        evaluate_escalation(cfg, "job", False, now=1001.0)
        result = evaluate_escalation(cfg, "job", False, now=2000.0)
        assert result is True

    def test_summary_contains_job(self, tmp_path):
        cfg = self._cfg(tmp_path)
        s = escalation_summary(cfg, "myjob")
        assert "myjob" in s
        assert "threshold=3" in s
