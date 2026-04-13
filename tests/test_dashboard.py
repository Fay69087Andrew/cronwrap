"""Tests for cronwrap.dashboard."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from cronwrap.dashboard import JobSummary, render_dashboard, summarise
from cronwrap.history import HistoryEntry


def _entry(
    command: str = "echo hi",
    exit_code: int = 0,
    ran_at: str = "2024-01-01T00:00:00",
    duration: float = 1.0,
    stdout: str = "",
    stderr: str = "",
) -> HistoryEntry:
    return HistoryEntry(
        command=command,
        exit_code=exit_code,
        ran_at=ran_at,
        duration=duration,
        stdout=stdout,
        stderr=stderr,
    )


class TestJobSummary:
    def test_success_rate_all_pass(self):
        s = JobSummary("cmd", total_runs=4, successes=4, failures=0, last_exit_code=0, last_ran_at="t")
        assert s.success_rate == 100.0

    def test_success_rate_all_fail(self):
        s = JobSummary("cmd", total_runs=3, successes=0, failures=3, last_exit_code=1, last_ran_at="t")
        assert s.success_rate == 0.0

    def test_success_rate_zero_runs(self):
        s = JobSummary("cmd", total_runs=0, successes=0, failures=0, last_exit_code=0, last_ran_at="t")
        assert s.success_rate == 0.0

    def test_str_ok_status(self):
        s = JobSummary("echo hi", total_runs=1, successes=1, failures=0, last_exit_code=0, last_ran_at="2024-01-01")
        assert "[OK]" in str(s)
        assert "echo hi" in str(s)

    def test_str_fail_status(self):
        s = JobSummary("bad cmd", total_runs=1, successes=0, failures=1, last_exit_code=2, last_ran_at="2024-01-01")
        assert "[FAIL]" in str(s)


class TestSummarise:
    def test_groups_by_command(self):
        entries = [
            _entry(command="cmd_a", exit_code=0),
            _entry(command="cmd_a", exit_code=1),
            _entry(command="cmd_b", exit_code=0),
        ]
        result = summarise(entries)
        commands = {s.command for s in result}
        assert commands == {"cmd_a", "cmd_b"}

    def test_counts_successes_and_failures(self):
        entries = [
            _entry(command="cmd", exit_code=0),
            _entry(command="cmd", exit_code=1),
            _entry(command="cmd", exit_code=0),
        ]
        (summary,) = summarise(entries)
        assert summary.total_runs == 3
        assert summary.successes == 2
        assert summary.failures == 1

    def test_last_exit_code_is_most_recent(self):
        entries = [
            _entry(command="cmd", exit_code=0, ran_at="2024-01-01T00:00:00"),
            _entry(command="cmd", exit_code=42, ran_at="2024-01-02T00:00:00"),
        ]
        (summary,) = summarise(entries)
        assert summary.last_exit_code == 42

    def test_empty_entries_returns_empty(self):
        assert summarise([]) == []


class TestRenderDashboard:
    def test_no_history_message(self):
        store = MagicMock()
        store.load.return_value = []
        output = render_dashboard(store)
        assert "No job history found" in output

    def test_dashboard_contains_command(self):
        store = MagicMock()
        store.load.return_value = [_entry(command="backup.sh", exit_code=0)]
        output = render_dashboard(store)
        assert "backup.sh" in output
        assert "cronwrap dashboard" in output

    def test_dashboard_passes_limit_to_store(self):
        store = MagicMock()
        store.load.return_value = []
        render_dashboard(store, limit=10)
        store.load.assert_called_once_with(limit=10)
