"""Tests for cronwrap.stagger and cronwrap.stagger_integration."""
import pytest
from unittest.mock import patch

from cronwrap.stagger import StaggerConfig, compute_stagger_delay, stagger_summary
from cronwrap.stagger_integration import apply_stagger, run_with_stagger


class TestStaggerConfig:
    def test_defaults(self):
        cfg = StaggerConfig()
        assert cfg.enabled is False
        assert cfg.window_seconds == 60
        assert cfg.job_id == "default"

    def test_zero_window_raises(self):
        with pytest.raises(ValueError, match="window_seconds"):
            StaggerConfig(window_seconds=0)

    def test_negative_window_raises(self):
        with pytest.raises(ValueError):
            StaggerConfig(window_seconds=-5)

    def test_empty_job_id_raises(self):
        with pytest.raises(ValueError, match="job_id"):
            StaggerConfig(job_id="   ")

    def test_job_id_stripped(self):
        cfg = StaggerConfig(job_id="  myjob  ")
        assert cfg.job_id == "myjob"

    def test_invalid_enabled_raises(self):
        with pytest.raises(TypeError):
            StaggerConfig(enabled="yes")  # type: ignore

    def test_from_env_defaults(self):
        with patch.dict("os.environ", {}, clear=False):
            cfg = StaggerConfig.from_env()
        assert cfg.enabled is False
        assert cfg.window_seconds == 60

    def test_from_env_enabled(self):
        env = {"CRONWRAP_STAGGER_ENABLED": "true", "CRONWRAP_STAGGER_WINDOW": "30", "CRONWRAP_STAGGER_JOB_ID": "backup"}
        with patch.dict("os.environ", env):
            cfg = StaggerConfig.from_env()
        assert cfg.enabled is True
        assert cfg.window_seconds == 30
        assert cfg.job_id == "backup"


class TestComputeStaggerDelay:
    def test_disabled_returns_zero(self):
        cfg = StaggerConfig(enabled=False, window_seconds=60, job_id="x")
        assert compute_stagger_delay(cfg) == 0.0

    def test_enabled_returns_value_in_range(self):
        cfg = StaggerConfig(enabled=True, window_seconds=60, job_id="myjob")
        delay = compute_stagger_delay(cfg)
        assert 0.0 <= delay < 60.0

    def test_deterministic(self):
        cfg = StaggerConfig(enabled=True, window_seconds=120, job_id="consistent")
        assert compute_stagger_delay(cfg) == compute_stagger_delay(cfg)

    def test_different_ids_differ(self):
        a = compute_stagger_delay(StaggerConfig(enabled=True, job_id="aaa"))
        b = compute_stagger_delay(StaggerConfig(enabled=True, job_id="bbb"))
        assert a != b


class TestStaggerSummary:
    def test_disabled_message(self):
        cfg = StaggerConfig(enabled=False)
        assert stagger_summary(cfg, 0.0) == "stagger disabled"

    def test_enabled_message_contains_fields(self):
        cfg = StaggerConfig(enabled=True, window_seconds=60, job_id="myjob")
        msg = stagger_summary(cfg, 12.34)
        assert "myjob" in msg
        assert "60s" in msg
        assert "12.34" in msg


class TestApplyStagger:
    def test_disabled_no_sleep(self):
        cfg = StaggerConfig(enabled=False)
        slept = []
        apply_stagger(cfg, sleep_fn=slept.append)
        assert slept == []

    def test_enabled_sleeps(self):
        cfg = StaggerConfig(enabled=True, window_seconds=60, job_id="job")
        slept = []
        delay = apply_stagger(cfg, sleep_fn=slept.append)
        assert len(slept) == 1
        assert slept[0] == pytest.approx(delay)


class TestRunWithStagger:
    def test_calls_fn_and_returns_result(self):
        cfg = StaggerConfig(enabled=False)
        result, summary = run_with_stagger(cfg, lambda: 42, sleep_fn=lambda _: None)
        assert result == 42
        assert "disabled" in summary

    def test_summary_present_when_enabled(self):
        cfg = StaggerConfig(enabled=True, window_seconds=30, job_id="t")
        _, summary = run_with_stagger(cfg, lambda: None, sleep_fn=lambda _: None)
        assert "stagger enabled" in summary
