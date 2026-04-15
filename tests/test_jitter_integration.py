"""Tests for cronwrap.jitter_integration."""
import random
import pytest

from cronwrap.jitter import JitterConfig
from cronwrap.jitter_integration import jittered_delays, jitter_summary, run_with_jitter
from cronwrap.runner import RunResult


def _result(exit_code: int) -> RunResult:
    return RunResult(command="echo test", exit_code=exit_code, stdout=b"", stderr=b"")


def _rng() -> random.Random:
    return random.Random(0)


class TestJitteredDelays:
    def test_returns_same_length(self):
        cfg = JitterConfig(strategy="none")
        result = jittered_delays([1.0, 2.0, 3.0], cfg)
        assert len(result) == 3

    def test_none_strategy_unchanged(self):
        cfg = JitterConfig(strategy="none")
        assert jittered_delays([1.0, 2.0], cfg) == [1.0, 2.0]

    def test_full_strategy_values_in_range(self):
        cfg = JitterConfig(strategy="full", max_jitter=10.0)
        delays = jittered_delays([3.0, 3.0, 3.0], cfg, _rng())
        for d in delays:
            assert 0.0 <= d <= 3.0


class TestRunWithJitter:
    def test_succeeds_first_attempt_no_sleep(self):
        slept: list[float] = []
        result, delays = run_with_jitter(
            lambda: _result(0),
            delays=[1.0, 2.0],
            cfg=JitterConfig(strategy="none"),
            _sleep=slept.append,
        )
        assert result.success
        assert slept == []

    def test_retries_on_failure_then_succeeds(self):
        calls = [_result(1), _result(0)]
        it = iter(calls)
        slept: list[float] = []
        result, delays = run_with_jitter(
            lambda: next(it),
            delays=[0.5],
            cfg=JitterConfig(strategy="none"),
            _sleep=slept.append,
        )
        assert result.success
        assert len(slept) == 1

    def test_exhausts_delays_on_persistent_failure(self):
        slept: list[float] = []
        result, delays = run_with_jitter(
            lambda: _result(1),
            delays=[0.1, 0.2],
            cfg=JitterConfig(strategy="none"),
            _sleep=slept.append,
        )
        assert not result.success
        assert len(slept) == 2

    def test_empty_delays_no_retry(self):
        slept: list[float] = []
        result, delays = run_with_jitter(
            lambda: _result(1),
            delays=[],
            cfg=JitterConfig(strategy="none"),
            _sleep=slept.append,
        )
        assert not result.success
        assert slept == []


class TestJitterSummary:
    def test_empty_delays(self):
        assert "No jittered" in jitter_summary([])

    def test_includes_attempt_count(self):
        summary = jitter_summary([1.0, 2.0])
        assert "2 attempt" in summary

    def test_includes_total(self):
        summary = jitter_summary([1.5, 2.5])
        assert "4.00s" in summary
