"""Tests for cronwrap.history module."""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from cronwrap.history import (
    HistoryEntry,
    HistoryStore,
    make_entry,
    MAX_HISTORY_ENTRIES,
)


def _entry(**kwargs) -> HistoryEntry:
    defaults = dict(
        command="echo hi",
        exit_code=0,
        started_at="2024-01-01T00:00:00+00:00",
        duration_seconds=0.5,
        attempts=1,
        stdout="hi",
        stderr="",
    )
    defaults.update(kwargs)
    return HistoryEntry(**defaults)


class TestHistoryEntry:
    def test_succeeded_true_on_zero_exit(self):
        assert _entry(exit_code=0).succeeded is True

    def test_succeeded_false_on_nonzero_exit(self):
        assert _entry(exit_code=1).succeeded is False

    def test_roundtrip_dict(self):
        e = _entry()
        assert HistoryEntry.from_dict(e.to_dict()) == e

    def test_to_dict_contains_expected_keys(self):
        keys = _entry().to_dict().keys()
        assert {"command", "exit_code", "started_at", "duration_seconds"}.issubset(keys)


class TestMakeEntry:
    def test_utc_iso_format(self):
        dt = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        e = make_entry("ls", 0, dt, 1.2)
        assert e.started_at == "2024-06-15T12:00:00+00:00"

    def test_duration_rounded(self):
        dt = datetime(2024, 1, 1, tzinfo=timezone.utc)
        e = make_entry("ls", 0, dt, 1.23456789)
        assert e.duration_seconds == 1.235

    def test_defaults_attempts_one(self):
        dt = datetime(2024, 1, 1, tzinfo=timezone.utc)
        e = make_entry("ls", 0, dt, 0.1)
        assert e.attempts == 1


class TestHistoryStore:
    def test_load_missing_file_gives_empty(self, tmp_path):
        store = HistoryStore(path=str(tmp_path / "missing.json"))
        store.load()
        assert store.entries() == []

    def test_record_and_retrieve(self, tmp_path):
        store = HistoryStore(path=str(tmp_path / "h.json"))
        store.load()
        e = _entry()
        store.record(e)
        assert store.entries() == [e]

    def test_save_and_reload(self, tmp_path):
        path = str(tmp_path / "h.json")
        store = HistoryStore(path=path)
        store.load()
        store.record(_entry(command="echo save"))
        store.save()

        store2 = HistoryStore(path=path)
        store2.load()
        assert len(store2.entries()) == 1
        assert store2.entries()[0].command == "echo save"

    def test_max_entries_trimmed(self, tmp_path):
        store = HistoryStore(path=str(tmp_path / "h.json"), max_entries=3)
        store.load()
        for i in range(5):
            store.record(_entry(command=f"cmd{i}"))
        assert len(store.entries()) == 3
        assert store.entries()[-1].command == "cmd4"

    def test_last_returns_n_entries(self, tmp_path):
        store = HistoryStore(path=str(tmp_path / "h.json"))
        store.load()
        for i in range(10):
            store.record(_entry(command=f"cmd{i}"))
        assert len(store.last(3)) == 3

    def test_load_corrupt_file_gives_empty(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text("not json")
        store = HistoryStore(path=str(p))
        store.load()
        assert store.entries() == []
