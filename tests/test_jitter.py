"""Tests for cronwrap.jitter."""
import random
import pytest

from cronwrap.jitter import JitterConfig, apply_jitter, _STRATEGIES


class TestJitterConfig:
    def test_defaults(self):
        cfg = JitterConfig()
        assert cfg.strategy == "full"
        assert cfg.max_jitter == 5.0
        assert cfg.seed is None

    def test_strategy_lowercased(self):
        cfg = JitterConfig(strategy="FULL")
        assert cfg.strategy == "full"

    def test_invalid_strategy_raises(self):
        with pytest.raises(ValueError, match="strategy"):
            JitterConfig(strategy="bogus")

    def test_negative_max_jitter_raises(self):
        with pytest.raises(ValueError, match="max_jitter"):
            JitterConfig(max_jitter=-1.0)

    def test_from_env_defaults(self, monkeypatch):
        for k in ("CRONWRAP_JITTER_STRATEGY", "CRONWRAP_JITTER_MAX", "CRONWRAP_JITTER_SEED"):
            monkeypatch.delenv(k, raising=False)
        cfg = JitterConfig.from_env()
        assert cfg.strategy == "full"
        assert cfg.max_jitter == 5.0
        assert cfg.seed is None

    def test_from_env_custom(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_JITTER_STRATEGY", "equal")
        monkeypatch.setenv("CRONWRAP_JITTER_MAX", "3.0")
        monkeypatch.setenv("CRONWRAP_JITTER_SEED", "42")
        cfg = JitterConfig.from_env()
        assert cfg.strategy == "equal"
        assert cfg.max_jitter == 3.0
        assert cfg.seed == 42


class TestApplyJitter:
    def _rng(self, seed: int = 0) -> random.Random:
        return random.Random(seed)

    def test_none_strategy_returns_base(self):
        cfg = JitterConfig(strategy="none")
        assert apply_jitter(2.5, cfg) == 2.5

    def test_full_result_between_zero_and_base(self):
        cfg = JitterConfig(strategy="full", max_jitter=10.0)
        result = apply_jitter(4.0, cfg, self._rng())
        assert 0.0 <= result <= 4.0

    def test_full_capped_by_max_jitter(self):
        cfg = JitterConfig(strategy="full", max_jitter=1.0)
        result = apply_jitter(100.0, cfg, self._rng())
        assert 0.0 <= result <= 1.0

    def test_equal_result_at_least_half_base(self):
        cfg = JitterConfig(strategy="equal", max_jitter=10.0)
        result = apply_jitter(4.0, cfg, self._rng())
        assert result >= 2.0

    def test_decorrelated_result_at_least_base(self):
        cfg = JitterConfig(strategy="decorrelated", max_jitter=10.0)
        result = apply_jitter(2.0, cfg, self._rng())
        assert result >= 2.0

    def test_negative_base_delay_raises(self):
        cfg = JitterConfig()
        with pytest.raises(ValueError, match="base_delay"):
            apply_jitter(-1.0, cfg)

    def test_zero_base_returns_zero_for_full(self):
        cfg = JitterConfig(strategy="full")
        assert apply_jitter(0.0, cfg, self._rng()) == 0.0

    def test_seed_produces_deterministic_output(self):
        cfg = JitterConfig(strategy="full", max_jitter=10.0, seed=99)
        r1 = apply_jitter(8.0, cfg)
        r2 = apply_jitter(8.0, cfg)
        assert r1 == r2
