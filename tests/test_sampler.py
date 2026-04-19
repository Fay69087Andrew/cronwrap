"""Tests for cronwrap.sampler and cronwrap.sampler_integration."""
from __future__ import annotations

import random
import sys
import pytest

from cronwrap.sampler import SamplerConfig, sampler_summary, should_sample
from cronwrap.sampler_integration import run_with_sampler, check_sample_or_skip


# ---------------------------------------------------------------------------
# TestSamplerConfig
# ---------------------------------------------------------------------------

class TestSamplerConfig:
    def test_defaults(self):
        cfg = SamplerConfig()
        assert cfg.rate == 1.0
        assert cfg.enabled is True
        assert cfg.seed is None

    def test_rate_below_zero_raises(self):
        with pytest.raises(ValueError):
            SamplerConfig(rate=-0.1)

    def test_rate_above_one_raises(self):
        with pytest.raises(ValueError):
            SamplerConfig(rate=1.1)

    def test_boundary_zero_accepted(self):
        cfg = SamplerConfig(rate=0.0)
        assert cfg.rate == 0.0

    def test_boundary_one_accepted(self):
        cfg = SamplerConfig(rate=1.0)
        assert cfg.rate == 1.0

    def test_invalid_enabled_raises(self):
        with pytest.raises(TypeError):
            SamplerConfig(enabled="yes")  # type: ignore

    def test_from_env_defaults(self, monkeypatch):
        for key in ("CRONWRAP_SAMPLE_RATE", "CRONWRAP_SAMPLE_ENABLED", "CRONWRAP_SAMPLE_SEED"):
            monkeypatch.delenv(key, raising=False)
        cfg = SamplerConfig.from_env()
        assert cfg.rate == 1.0
        assert cfg.enabled is True
        assert cfg.seed is None

    def test_from_env_custom(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_SAMPLE_RATE", "0.5")
        monkeypatch.setenv("CRONWRAP_SAMPLE_ENABLED", "false")
        monkeypatch.setenv("CRONWRAP_SAMPLE_SEED", "42")
        cfg = SamplerConfig.from_env()
        assert cfg.rate == 0.5
        assert cfg.enabled is False
        assert cfg.seed == 42


# ---------------------------------------------------------------------------
# TestShouldSample
# ---------------------------------------------------------------------------

class TestShouldSample:
    def test_always_runs_at_rate_one(self):
        cfg = SamplerConfig(rate=1.0)
        assert all(should_sample(cfg) for _ in range(20))

    def test_never_runs_at_rate_zero(self):
        cfg = SamplerConfig(rate=0.0)
        assert not any(should_sample(cfg) for _ in range(20))

    def test_disabled_always_runs(self):
        cfg = SamplerConfig(rate=0.0, enabled=False)
        assert should_sample(cfg) is True

    def test_deterministic_with_seed(self):
        cfg = SamplerConfig(rate=0.5, seed=99)
        rng = random.Random(99)
        result = should_sample(cfg, rng=rng)
        assert isinstance(result, bool)

    def test_custom_rng_used(self):
        cfg = SamplerConfig(rate=0.5)
        always_true_rng = random.Random()
        always_true_rng.random = lambda: 0.0  # type: ignore
        assert should_sample(cfg, rng=always_true_rng) is True


# ---------------------------------------------------------------------------
# TestSamplerSummary
# ---------------------------------------------------------------------------

class TestSamplerSummary:
    def test_selected_message(self):
        cfg = SamplerConfig(rate=0.5)
        msg = sampler_summary(cfg, sampled=True)
        assert "selected" in msg
        assert "0.50" in msg

    def test_skipped_message(self):
        cfg = SamplerConfig(rate=0.5)
        msg = sampler_summary(cfg, sampled=False)
        assert "skipped" in msg

    def test_disabled_message(self):
        cfg = SamplerConfig(enabled=False)
        msg = sampler_summary(cfg, sampled=True)
        assert "disabled" in msg


# ---------------------------------------------------------------------------
# TestRunWithSampler
# ---------------------------------------------------------------------------

class TestRunWithSampler:
    def test_runs_fn_when_sampled(self):
        cfg = SamplerConfig(rate=1.0)
        called = []
        result, summary = run_with_sampler(cfg, lambda: called.append(1) or "ok")
        assert result == "ok"
        assert "selected" in summary

    def test_skips_fn_when_not_sampled(self):
        cfg = SamplerConfig(rate=0.0)
        called = []
        result, summary = run_with_sampler(cfg, lambda: called.append(1))
        assert result is None
        assert not called
        assert "skipped" in summary

    def test_check_sample_or_skip_exits_when_skipped(self):
        cfg = SamplerConfig(rate=0.0)
        with pytest.raises(SystemExit) as exc:
            check_sample_or_skip(cfg)
        assert exc.value.code == 0

    def test_check_sample_or_skip_returns_true_when_selected(self):
        cfg = SamplerConfig(rate=1.0)
        assert check_sample_or_skip(cfg) is True
