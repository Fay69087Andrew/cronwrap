"""Tests for cronwrap.metrics."""
import time

import pytest

from cronwrap.metrics import JobMetric, MetricsStore, get_store


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _metric(command="echo hi", exit_code=0, duration=1.23, ts=None) -> JobMetric:
    m = JobMetric(command=command, exit_code=exit_code, duration_seconds=duration)
    if ts is not None:
        m.timestamp = ts
    return m


# ---------------------------------------------------------------------------
# JobMetric
# ---------------------------------------------------------------------------

class TestJobMetric:
    def test_succeeded_on_zero_exit(self):
        assert _metric(exit_code=0).succeeded is True

    def test_not_succeeded_on_nonzero_exit(self):
        assert _metric(exit_code=1).succeeded is False

    def test_to_dict_keys(self):
        d = _metric().to_dict()
        assert set(d.keys()) == {"command", "exit_code", "duration_seconds", "timestamp", "succeeded"}

    def test_to_dict_duration_rounded(self):
        d = _metric(duration=1.123456789).to_dict()
        assert d["duration_seconds"] == round(1.123456789, 4)

    def test_timestamp_auto_set(self):
        before = time.time()
        m = _metric()
        assert m.timestamp >= before

    def test_to_dict_values_match_fields(self):
        """Ensure to_dict values are consistent with the object's own fields."""
        m = _metric(command="ls -la", exit_code=2, duration=0.5)
        d = m.to_dict()
        assert d["command"] == m.command
        assert d["exit_code"] == m.exit_code
        assert d["succeeded"] == m.succeeded
        assert d["timestamp"] == m.timestamp


# ---------------------------------------------------------------------------
# MetricsStore
# ---------------------------------------------------------------------------

class TestMetricsStore:
    def setup_method(self):
        self.store = MetricsStore()

    def test_initially_empty(self):
        assert self.store.all() == []

    def test_record_appends(self):
        self.store.record(_metric())
        assert len(self.store.all()) == 1

    def test_for_command_filters(self):
        self.store.record(_metric(command="job_a"))
        self.store.record(_metric(command="job_b"))
        assert len(self.store.for_command("job_a")) == 1

    def test_for_command_no_match_returns_empty(self):
        """for_command should return an empty list when no metrics match."""
        self.store.record(_metric(command="job_a"))
        assert self.store.for_command("nonexistent") == []

    def test_summary_empty(self):
        s = self.store.summary()
        assert s["total"] == 0
        assert s["avg_duration"] is None

    def test_summary_counts(self):
        self.store.record(_metric(exit_code=0))
        self.store.record(_metric(exit_code=0))
        self.store.record(_metric(exit_code=1))
        s = self.store.summary()
        assert s["total"] == 3
        assert s["succeeded"] == 2
        assert s["failed"] == 1

    def test_summary_avg_duration(self):
        self.store.record(_metric(duration=2.0))
        self.store.record(_metric(duration=4.0))
        assert self.store.summary()["avg_duration"] == 3.0

    def test_clear_removes_all(self):
        self.store.record(_metric())
        self.store.clear()
        assert self.store.all() == []

    def test_all_returns_copy(self):
        self.store.record(_metric())
        copy = self.store.all()
        copy.clear()
        assert len(self.store.all()) == 1


# --------
