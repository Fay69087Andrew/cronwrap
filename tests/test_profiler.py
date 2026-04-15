"""Tests for cronwrap.profiler."""
import pytest
from cronwrap.profiler import Profiler, ProfilerConfig, ProfileResult


class TestProfilerConfig:
    def test_defaults(self):
        cfg = ProfilerConfig()
        assert cfg.enabled is True
        assert cfg.warn_threshold_seconds == 60.0
        assert cfg.critical_threshold_seconds == 300.0

    def test_zero_warn_raises(self):
        with pytest.raises(ValueError, match="warn_threshold_seconds must be positive"):
            ProfilerConfig(warn_threshold_seconds=0)

    def test_negative_warn_raises(self):
        with pytest.raises(ValueError, match="warn_threshold_seconds must be positive"):
            ProfilerConfig(warn_threshold_seconds=-1)

    def test_zero_critical_raises(self):
        with pytest.raises(ValueError, match="critical_threshold_seconds must be positive"):
            ProfilerConfig(critical_threshold_seconds=0)

    def test_critical_less_than_warn_ pytest.raises(ValueError, match="critical_threshold_seconds must be"):
            ProfilerConfig(warn_threshold_seconds=100, critical_threshold_seconds=50)

    def test_from_env_defaults(self):
        cfg = ProfilerConfig.from_env({})
        assert cfg.enabled is True
        assert cfg.warn_threshold_seconds == 60.0
        assert cfg.critical_threshold_seconds == 300.0

    def test_from_env_disabled(self):
        cfg = ProfilerConfig.from_env({"CRONWRAP_PROFILER_ENABLED": "false"})
        assert cfg.enabled is False

    def test_from_env_custom_thresholds(self):
        cfg = ProfilerConfig.from_env({
            "CRONWRAP_PROFILER_WARN_SECONDS": "30",
            "CRONWRAP_PROFILER_CRITICAL_SECONDS": "120",
        })
        assert cfg.warn_threshold_seconds == 30.0
        assert cfg.critical_threshold_seconds == 120.0


class TestProfileResult:
    def _make(self, elapsed, warn=60.0, critical=300.0, label=""):
        return=elapsed,
            warn_threshold_seconds=warn,
            critical_threshold_seconds=critical,
            label=label,
        )

    def test_level_ok(self):
        assert self._make(10level == "ok"

    def test_level_warn(self):
        assert self._make(90).level == "warn"

    def test_level_critical(self):
        assert self._make(400).level == "critical"

    def test_level_at_warn_boundary(self):
        assert self._make(60.0).level == "warn"

    def test_level_at_critical_boundary(self):
        assert self._make(300.0).level == "critical"

    def test_summary_includes_elapsed(self):
        r = self._make(12.5)
        assert "12.500s" in r.summary()

    def test_summary_includes_level(self):
        r = self._make(10)
        assert "level=ok" in r.summary(summary_includes_label(self):
        r = self._make(10, label="my-job")
        assert "[my-job]" in r.summary()

    def test_summary_no_label_prefix(self):
        r = self._make(10, label="")
        assert r.summary().startswith("elapsed="nclass TestProfiler:
    def test_measures_elapsed(self):
        cfg = ProfilerConfig()
        with Profiler(cfg) as p:
            pass
        assert p.result is not None
        assert p.result.elapsed_seconds >= 0.0

    def test_result_level_ok_for_fast_job(self):
        cfg = ProfilerConfig(warn_threshold_seconds=60)
        with Profiler(cfg) as p:
            pass
        assert p.result.level == "ok"

    def test_label_passed_to_result(self):
        cfg = ProfilerConfig()
        with Profiler(cfg, label="test-label") as p:
            pass
        assert p.result.label == "test-label"
