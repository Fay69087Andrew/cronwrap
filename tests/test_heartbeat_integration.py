"""Tests for cronwrap.heartbeat_integration."""

from __future__ import annotations

from cronwrap.heartbeat import HeartbeatConfig, HeartbeatWorker
from cronwrap.heartbeat_integration import (
    build_heartbeat,
    heartbeat_summary,
    run_with_heartbeat,
)
from cronwrap.runner import RunResult


def _result(exit_code: int = 0) -> RunResult:
    return RunResult(command="echo hi", exit_code=exit_code, stdout=b"hi", stderr=b"")


def _cfg(url="https://ping.example.com", interval=0.05):
    return HeartbeatConfig(url=url, interval=interval, timeout=5.0)


class TestRunWithHeartbeat:
    def test_returns_result_and_summary(self):
        calls = []
        result, summary = run_with_heartbeat(
            _cfg(),
            job=lambda: _result(0),
            ping_fn=lambda u, t: calls.append(u),
        )
        assert result.exit_code == 0
        assert "url" in summary

    def test_pings_during_job(self):
        import time
        calls = []

        def slow_job():
            time.sleep(0.18)
            return _result(0)

        _, summary = run_with_heartbeat(
            _cfg(interval=0.05),
            job=slow_job,
            ping_fn=lambda u, t: calls.append(u),
        )
        assert summary["ping_count"] >= 2

    def test_job_failure_still_stops_worker(self):
        import pytest
        calls = []
        with pytest.raises(RuntimeError):
            run_with_heartbeat(
                _cfg(),
                job=lambda: (_ for _ in ()).throw(RuntimeError("boom")),
                ping_fn=lambda u, t: calls.append(u),
            )


class TestHeartbeatSummary:
    def test_summary_contains_url(self):
        w = HeartbeatWorker(_cfg())
        text = heartbeat_summary(w)
        assert "https://ping.example.com" in text

    def test_summary_shows_none_error_when_clean(self):
        w = HeartbeatWorker(_cfg())
        text = heartbeat_summary(w)
        assert "none" in text


class TestBuildHeartbeat:
    def test_returns_worker(self):
        w = build_heartbeat(env=False, url="https://x.com")
        assert isinstance(w, HeartbeatWorker)

    def test_override_applied(self):
        w = build_heartbeat(env=False, url="https://override.com", interval=15.0)
        assert w._config.url == "https://override.com"
        assert w._config.interval == 15.0
