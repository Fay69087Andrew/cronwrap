"""Tests for cronwrap.spillover."""
import pytest

from cronwrap.spillover import (
    SpilloverConfig,
    SpilloverResult,
    check_spillover,
    spillover_summary,
)


class TestSpilloverConfig:
    def test_defaults(self):
        cfg = SpilloverConfig()
        assert cfg.interval_seconds == 3600.0
        assert cfg.enabled is True
        assert cfg.warn_only is True

    def test_zero_interval_raises(self):
        with pytest.raises(ValueError, match="interval_seconds must be positive"):
            SpilloverConfig(interval_seconds=0)

    def test_negative_interval_raises(self):
        with pytest.raises(ValueError, match="interval_seconds must be positive"):
            SpilloverConfig(interval_seconds=-1)

    def test_invalid_enabled_raises(self):
        with pytest.raises(TypeError, match="enabled must be a bool"):
            SpilloverConfig(enabled="yes")  # type: ignore

    def test_invalid_warn_only_raises(self):
        with pytest.raises(TypeError, match="warn_only must be a bool"):
            SpilloverConfig(warn_only=1)  # type: ignore

    def test_from_env_defaults(self, monkeypatch):
        for key in (
            "CRONWRAP_SPILLOVER_ENABLED",
            "CRONWRAP_SPILLOVER_WARN_ONLY",
            "CRONWRAP_SPILLOVER_INTERVAL",
        ):
            monkeypatch.delenv(key, raising=False)
        cfg = SpilloverConfig.from_env()
        assert cfg.enabled is True
        assert cfg.warn_only is True
        assert cfg.interval_seconds == 3600.0

    def test_from_env_custom(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_SPILLOVER_ENABLED", "false")
        monkeypatch.setenv("CRONWRAP_SPILLOVER_WARN_ONLY", "false")
        monkeypatch.setenv("CRONWRAP_SPILLOVER_INTERVAL", "600")
        cfg = SpilloverConfig.from_env()
        assert cfg.enabled is False
        assert cfg.warn_only is False
        assert cfg.interval_seconds == 600.0


class TestSpilloverResult:
    def test_no_spillover(self):
        r = SpilloverResult(elapsed_seconds=60.0, interval_seconds=3600.0, spilled=False)
        assert r.overflow_seconds == 0.0
        assert "OK" in str(r)

    def test_spillover_overflow(self):
        r = SpilloverResult(elapsed_seconds=4000.0, interval_seconds=3600.0, spilled=True)
        assert r.overflow_seconds == pytest.approx(400.0)
        assert "SPILLOVER" in str(r)
        assert "400.0s" in str(r)

    def test_overflow_never_negative(self):
        r = SpilloverResult(elapsed_seconds=100.0, interval_seconds=3600.0, spilled=False)
        assert r.overflow_seconds == 0.0


class TestCheckSpillover:
    def test_no_spill_when_within_interval(self):
        cfg = SpilloverConfig(interval_seconds=3600.0)
        result = check_spillover(3599.0, cfg)
        assert result.spilled is False

    def test_spill_when_over_interval(self):
        cfg = SpilloverConfig(interval_seconds=3600.0)
        result = check_spillover(3601.0, cfg)
        assert result.spilled is True

    def test_no_spill_when_disabled(self):
        cfg = SpilloverConfig(interval_seconds=60.0, enabled=False)
        result = check_spillover(9999.0, cfg)
        assert result.spilled is False

    def test_exact_boundary_not_spill(self):
        cfg = SpilloverConfig(interval_seconds=100.0)
        result = check_spillover(100.0, cfg)
        assert result.spilled is False

    def test_default_config_used_when_none(self):
        result = check_spillover(1.0)
        assert result.interval_seconds == 3600.0


class TestSpilloverSummary:
    def test_keys_present(self):
        r = SpilloverResult(elapsed_seconds=50.0, interval_seconds=100.0, spilled=False)
        s = spillover_summary(r)
        assert set(s.keys()) == {"spilled", "elapsed_seconds", "interval_seconds", "overflow_seconds"}

    def test_values_correct(self):
        r = SpilloverResult(elapsed_seconds=150.0, interval_seconds=100.0, spilled=True)
        s = spillover_summary(r)
        assert s["spilled"] is True
        assert s["overflow_seconds"] == pytest.approx(50.0)
