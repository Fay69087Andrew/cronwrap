"""Tests for cronwrap.audit_report."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from cronwrap.audit import AuditEntry
from cronwrap.audit_report import summarise_job, render_report


_T0 = datetime(2024, 3, 1, 8, 0, 0, tzinfo=timezone.utc)
_T1 = datetime(2024, 3, 1, 8, 0, 10, tzinfo=timezone.utc)


def _e(exit_code: int = 0, duration: float = 10.0, attempt: int = 1) -> AuditEntry:
    from datetime import timedelta
    return AuditEntry(
        job_name="myjob",
        command="echo hi",
        exit_code=exit_code,
        stdout="",
        stderr="",
        started_at=_T0,
        finished_at=_T0 + timedelta(seconds=duration),
        attempt=attempt,
    )


class TestSummariseJob:
    def test_empty_returns_empty_dict(self):
        assert summarise_job([]) == {}

    def test_all_success(self):
        entries = [_e(0), _e(0), _e(0)]
        s = summarise_job(entries)
        assert s["successes"] == 3
        assert s["failures"] == 0
        assert s["success_rate"] == 100.0

    def test_all_failure(self):
        entries = [_e(1), _e(2)]
        s = summarise_job(entries)
        assert s["successes"] == 0
        assert s["success_rate"] == 0.0

    def test_mixed(self):
        entries = [_e(0), _e(1), _e(0), _e(1)]
        s = summarise_job(entries)
        assert s["success_rate"] == 50.0

    def test_avg_duration(self):
        entries = [_e(duration=10.0), _e(duration=20.0)]
        s = summarise_job(entries)
        assert s["avg_duration_seconds"] == 15.0

    def test_max_duration(self):
        entries = [_e(duration=5.0), _e(duration=30.0)]
        s = summarise_job(entries)
        assert s["max_duration_seconds"] == 30.0

    def test_last_run_is_most_recent(self):
        from datetime import timedelta
        e1 = _e()
        e2 = AuditEntry(
            job_name="myjob", command="echo", exit_code=0,
            stdout="", stderr="",
            started_at=_T0 + timedelta(hours=1),
            finished_at=_T0 + timedelta(hours=1, seconds=5),
        )
        s = summarise_job([e1, e2])
        assert s["last_run_at"] == e2.finished_at


class TestRenderReport:
    def test_empty_entries_message(self):
        out = render_report("myjob", [])
        assert "No audit entries" in out

    def test_contains_job_name(self):
        out = render_report("myjob", [_e()])
        assert "myjob" in out

    def test_contains_success_rate(self):
        out = render_report("myjob", [_e(0), _e(1)])
        assert "50.0%" in out

    def test_contains_ok_and_fail_markers(self):
        out = render_report("myjob", [_e(0), _e(1)])
        assert "OK" in out
        assert "FAIL" in out

    def test_at_most_10_recent_runs_shown(self):
        entries = [_e() for _ in range(15)]
        out = render_report("myjob", entries)
        assert out.count("[OK]") == 10
