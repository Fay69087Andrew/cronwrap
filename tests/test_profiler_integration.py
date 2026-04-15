"""Tests for cronwrap.profiler_integration."""
from unittest.mock import MagicMock
import pytest
from cronwrap.profiler import ProfilerConfig, ProfileResult
from cronwrap.profiler_integration import (
    build_profiler_config,
    profile_result,
    run_with_profiler,
    profiler_summary,
)


def _run_result(command="echo hi", exit_code=0, elapsed=5.0):
    r = MagicMock()
    r.command = command
    r.exit_code = exit_code
    r.elapsed_seconds = elapsed
    return r


class TestBuildProfilerConfig:
    def test_returns_profiler_config(self):
        cfg = build_profiler_config({})
        assert isinstance(cfg, ProfilerConfig)

    def test_custom_env_applied(self):
        cfg = build_profiler_config({"CRONWRAP_PROFILER_WARN_SECONDS": "45"})
        assert cfg.warn_threshold_seconds == 45.0


class TestProfileResult:
    def test_uses_elapsed_from_result(self):
        r = _run_result(elapsed=42.0)
        cfg = ProfilerConfig()
        pr = profile_result(r, cfg, label="lbl")
        assert pr.elapsed_seconds == 42.0

    def test_label_from_argument(self):
        r = _run_result()
        cfg = ProfilerConfig()
        pr = profile_result(r, cfg, label="custom")
        assert pr.label == "custom"

    def test_label_falls_back_to_command(self):
        r = _run_result(command="my-cmd")
        cfg = ProfilerConfig()
        pr = profile_result(r, cfg)
        assert pr.label == "my-cmd"


class TestRunWithProfiler:
    def test_returns_run_result_and_profile(self):
        run_result = _run_result()
        cfg = ProfilerConfig()
        result, profile = run_with_profiler(lambda: run_result, cfg, label="job")
        assert result is run_result
        assert isinstance(profile, ProfileResult)

    def test_elapsed_is_non_negative(self):
        cfg = ProfilerConfig()
        _, profile = run_with_profiler(lambda: _run_result(), cfg)
        assert profile.elapsed_seconds >= 0.0

    def test_label_propagated(self):
        cfg = ProfilerConfig()
        _, profile = run_with_profiler(lambda: _run_result(), cfg, label="my-label")
        assert profile.label == "my-label"


class TestProfilerSummary:
    def test_returns_string(self):
        pr = ProfileResult(
            elapsed_seconds=10.0,
            warn_threshold_seconds=60.0,
            critical_threshold_seconds=300.0,
        )
        s = profiler_summary(pr)
        assert isinstance(s, str)
        assert "10.000s" in s
