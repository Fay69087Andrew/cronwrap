"""Tests for cronwrap.splay."""
import pytest
from unittest.mock import patch

from cronwrap.splay import SplayConfig, compute_splay, apply_splay, splay_summary


class TestSplayConfig:
    def test_defaults(self):
        cfg = SplayConfig()
        assert cfg.max_seconds == 0
        assert cfg.enabled is True
        assert cfg.seed is None

    def test_negative_max_seconds_raises(self):
        with pytest.raises(ValueError, match="max_seconds"):
            SplayConfig(max_seconds=-1)

    def test_invalid_enabled_raises(self):
        with pytest.raises(TypeError):
            SplayConfig(enabled="yes")  # type: ignore

    def test_from_env_defaults(self, monkeypatch):
        for k in ("CRONWRAP_SPLAY_ENABLED", "CRONWRAP_SPLAY_MAX_SECONDS", "CRONWRAP_SPLAY_SEED"):
            monkeypatch.delenv(k, raising=False)
        cfg = SplayConfig.from_env()
        assert cfg.max_seconds == 0
        assert cfg.enabled is True
        assert cfg.seed is None

    def test_from_env_custom(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_SPLAY_ENABLED", "true")
        monkeypatch.setenv("CRONWRAP_SPLAY_MAX_SECONDS", "30")
        monkeypatch.setenv("CRONWRAP_SPLAY_SEED", "42")
        cfg = SplayConfig.from_env()
        assert cfg.max_seconds == 30
        assert cfg.seed == 42

    def test_from_env_disabled(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_SPLAY_ENABLED", "false")
        cfg = SplayConfig.from_env()
        assert cfg.enabled is False


class TestComputeSplay:
    def test_zero_when_disabled(self):
        cfg = SplayConfig(max_seconds=60, enabled=False)
        assert compute_splay(cfg) == 0.0

    def test_zero_when_max_is_zero(self):
        cfg = SplayConfig(max_seconds=0)
        assert compute_splay(cfg) == 0.0

    def test_within_range(self):
        cfg = SplayConfig(max_seconds=10, seed=7)
        delay = compute_splay(cfg)
        assert 0.0 <= delay <= 10.0

    def test_deterministic_with_seed(self):
        cfg = SplayConfig(max_seconds=20, seed=99)
        assert compute_splay(cfg) == compute_splay(cfg)


class TestApplySplay:
    def test_sleeps_for_computed_delay(self):
        slept = []
        cfg = SplayConfig(max_seconds=5, seed=1)
        delay = apply_splay(cfg, _sleep=slept.append)
        assert len(slept) == 1
        assert slept[0] == pytest.approx(delay)

    def test_no_sleep_when_disabled(self):
        slept = []
        cfg = SplayConfig(max_seconds=10, enabled=False)
        delay = apply_splay(cfg, _sleep=slept.append)
        assert delay == 0.0
        assert slept == []


class TestSplaySummary:
    def test_disabled_message(self):
        cfg = SplayConfig(max_seconds=0)
        assert splay_summary(cfg, 0.0) == "splay: disabled"

    def test_active_message(self):
        cfg = SplayConfig(max_seconds=30)
        msg = splay_summary(cfg, 12.345)
        assert "12.35" in msg
        assert "30" in msg
