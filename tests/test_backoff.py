"""Tests for cronwrap.backoff."""
from __future__ import annotations

import pytest

from cronwrap.backoff import BackoffConfig, compute_delay, delay_sequence


class TestBackoffConfig:
    def test_defaults(self):
        cfg = BackoffConfig()
        assert cfg.base == 2.0
        assert cfg.max_delay == 300.0
        assert cfg.jitter is True

    def test_base_must_be_greater_than_one(self):
        with pytest.raises(ValueError, match="base"):
            BackoffConfig(base=1.0)

    def test_base_of_zero_raises(self):
        with pytest.raises(ValueError):
            BackoffConfig(base=0.0)

    def test_max_delay_zero_raises(self):
        with pytest.raises(ValueError, match="max_delay"):
            BackoffConfig(max_delay=0.0)

    def test_max_delay_negative_raises(self):
        with pytest.raises(ValueError):
            BackoffConfig(max_delay=-1.0)

    def test_from_env_defaults(self):
        cfg = BackoffConfig.from_env(env={})
        assert cfg == BackoffConfig()

    def test_from_env_custom_values(self):
        env = {
            "CRONWRAP_BACKOFF_BASE": "3.0",
            "CRONWRAP_BACKOFF_MAX_DELAY": "60.0",
            "CRONWRAP_BACKOFF_JITTER": "false",
        }
        cfg = BackoffConfig.from_env(env=env)
        assert cfg.base == 3.0
        assert cfg.max_delay == 60.0
        assert cfg.jitter is False

    def test_from_env_jitter_truthy(self):
        cfg = BackoffConfig.from_env(env={"CRONWRAP_BACKOFF_JITTER": "1"})
        assert cfg.jitter is True


class TestComputeDelay:
    def _cfg(self, **kw):
        return BackoffConfig(jitter=False, **kw)

    def test_attempt_zero_returns_one(self):
        cfg = self._cfg(base=2.0)
        assert compute_delay(0, cfg) == pytest.approx(1.0)

    def test_attempt_one_returns_base(self):
        cfg = self._cfg(base=2.0)
        assert compute_delay(1, cfg) == pytest.approx(2.0)

    def test_attempt_three(self):
        cfg = self._cfg(base=2.0)
        assert compute_delay(3, cfg) == pytest.approx(8.0)

    def test_clamped_at_max_delay(self):
        cfg = self._cfg(base=2.0, max_delay=5.0)
        assert compute_delay(10, cfg) == pytest.approx(5.0)

    def test_jitter_reduces_delay(self):
        cfg = BackoffConfig(base=2.0, max_delay=300.0, jitter=True)
        delay = compute_delay(4, cfg, seed=42)
        assert delay < 2.0 ** 4
        assert delay > 0

    def test_jitter_seed_is_deterministic(self):
        cfg = BackoffConfig(base=2.0, jitter=True)
        d1 = compute_delay(5, cfg, seed=99)
        d2 = compute_delay(5, cfg, seed=99)
        assert d1 == d2


class TestDelaySequence:
    def test_length_matches_attempts(self):
        cfg = BackoffConfig(base=2.0, jitter=False)
        seq = delay_sequence(4, cfg)
        assert len(seq) == 4

    def test_values_are_increasing(self):
        cfg = BackoffConfig(base=2.0, max_delay=300.0, jitter=False)
        seq = delay_sequence(5, cfg)
        for a, b in zip(seq, seq[1:]):
            assert b >= a

    def test_empty_sequence(self):
        cfg = BackoffConfig(jitter=False)
        assert delay_sequence(0, cfg) == []
