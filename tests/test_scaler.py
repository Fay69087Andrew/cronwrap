"""Tests for cronwrap.scaler."""
import pytest
from cronwrap.scaler import ScalerConfig, evaluate_scale, scaler_summary


class TestScalerConfig:
    def test_defaults(self):
        cfg = ScalerConfig()
        assert cfg.enabled is True
        assert cfg.min_instances == 1
        assert cfg.max_instances == 4
        assert cfg.target_duration_seconds == 60.0
        assert cfg.scale_up_threshold == 1.5
        assert cfg.scale_down_threshold == 0.5
        assert cfg.window == 5

    def test_min_instances_zero_raises(self):
        with pytest.raises(ValueError, match="min_instances"):
            ScalerConfig(min_instances=0)

    def test_max_less_than_min_raises(self):
        with pytest.raises(ValueError, match="max_instances"):
            ScalerConfig(min_instances=3, max_instances=2)

    def test_zero_target_raises(self):
        with pytest.raises(ValueError, match="target_duration_seconds"):
            ScalerConfig(target_duration_seconds=0)

    def test_scale_up_threshold_at_one_raises(self):
        with pytest.raises(ValueError, match="scale_up_threshold"):
            ScalerConfig(scale_up_threshold=1.0)

    def test_scale_down_threshold_zero_raises(self):
        with pytest.raises(ValueError, match="scale_down_threshold"):
            ScalerConfig(scale_down_threshold=0.0)

    def test_window_zero_raises(self):
        with pytest.raises(ValueError, match="window"):
            ScalerConfig(window=0)

    def test_from_env_defaults(self, monkeypatch):
        for k in [
            "CRONWRAP_SCALER_ENABLED", "CRONWRAP_SCALER_MIN", "CRONWRAP_SCALER_MAX",
            "CRONWRAP_SCALER_TARGET", "CRONWRAP_SCALER_UP_THRESHOLD",
            "CRONWRAP_SCALER_DOWN_THRESHOLD", "CRONWRAP_SCALER_WINDOW",
        ]:
            monkeypatch.delenv(k, raising=False)
        cfg = ScalerConfig.from_env()
        assert cfg.enabled is True
        assert cfg.min_instances == 1


class TestEvaluateScale:
    def _cfg(self, **kw):
        return ScalerConfig(**kw)

    def test_no_durations_returns_noop(self):
        cfg = self._cfg()
        d = evaluate_scale(cfg, [], 2)
        assert d.reason == "no-op"
        assert d.recommended_instances == 2

    def test_disabled_returns_noop(self):
        cfg = self._cfg(enabled=False)
        d = evaluate_scale(cfg, [200.0], 2)
        assert d.reason == "no-op"

    def test_scale_up_when_avg_exceeds_threshold(self):
        cfg = self._cfg(target_duration_seconds=60.0, scale_up_threshold=1.5, max_instances=4)
        d = evaluate_scale(cfg, [100.0, 100.0], 2)
        assert d.reason == "scale-up"
        assert d.recommended_instances == 3

    def test_scale_up_capped_at_max(self):
        cfg = self._cfg(target_duration_seconds=60.0, scale_up_threshold=1.5, max_instances=2)
        d = evaluate_scale(cfg, [100.0], 2)
        assert d.recommended_instances == 2

    def test_scale_down_when_avg_below_threshold(self):
        cfg = self._cfg(target_duration_seconds=60.0, scale_down_threshold=0.5, min_instances=1)
        d = evaluate_scale(cfg, [10.0, 10.0], 3)
        assert d.reason == "scale-down"
        assert d.recommended_instances == 2

    def test_scale_down_capped_at_min(self):
        cfg = self._cfg(target_duration_seconds=60.0, scale_down_threshold=0.5, min_instances=1)
        d = evaluate_scale(cfg, [10.0], 1)
        assert d.recommended_instances == 1

    def test_stable_when_within_thresholds(self):
        cfg = self._cfg(target_duration_seconds=60.0)
        d = evaluate_scale(cfg, [60.0], 2)
        assert d.reason == "stable"
        assert d.recommended_instances == 2

    def test_window_limits_durations_used(self):
        cfg = self._cfg(target_duration_seconds=60.0, window=2, scale_up_threshold=1.5)
        # old durations are slow, recent ones are fast
        d = evaluate_scale(cfg, [200.0, 200.0, 10.0, 10.0], 2)
        assert d.reason == "scale-down"

    def test_str_representation(self):
        cfg = self._cfg()
        d = evaluate_scale(cfg, [60.0], 2)
        assert "stable" in str(d)

    def test_summary_string(self):
        cfg = self._cfg()
        d = evaluate_scale(cfg, [90.0], 2)
        s = scaler_summary(d)
        assert "scaler:" in s
        assert "recommended" in s
