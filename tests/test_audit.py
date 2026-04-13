"""Tests for cronwrap.audit."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from cronwrap.audit import AuditConfig, AuditEntry, AuditStore


_T0 = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
_T1 = datetime(2024, 1, 1, 12, 0, 5, tzinfo=timezone.utc)


def _entry(**kwargs) -> AuditEntry:
    defaults = dict(
        job_name="backup",
        command="/usr/bin/backup.sh",
        exit_code=0,
        stdout="ok",
        stderr="",
        started_at=_T0,
        finished_at=_T1,
    )
    defaults.update(kwargs)
    return AuditEntry(**defaults)


class TestAuditConfig:
    def test_defaults(self):
        cfg = AuditConfig()
        assert cfg.enabled is True
        assert cfg.max_entries == 10_000

    def test_invalid_max_entries_raises(self):
        with pytest.raises(ValueError, match="max_entries"):
            AuditConfig(max_entries=0)

    def test_from_env(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_AUDIT_ENABLED", "false")
        monkeypatch.setenv("CRONWRAP_AUDIT_MAX_ENTRIES", "500")
        cfg = AuditConfig.from_env()
        assert cfg.enabled is False
        assert cfg.max_entries == 500


class TestAuditEntry:
    def test_succeeded_true_on_zero_exit(self):
        assert _entry(exit_code=0).succeeded is True

    def test_succeeded_false_on_nonzero_exit(self):
        assert _entry(exit_code=1).succeeded is False

    def test_duration_seconds(self):
        e = _entry()
        assert e.duration_seconds == 5.0

    def test_roundtrip_dict(self):
        e = _entry(tags=["prod"], attempt=2)
        restored = AuditEntry.from_dict(e.to_dict())
        assert restored.job_name == e.job_name
        assert restored.exit_code == e.exit_code
        assert restored.attempt == 2
        assert restored.tags == ["prod"]

    def test_to_dict_contains_succeeded_key(self):
        d = _entry(exit_code=0).to_dict()
        assert "succeeded" in d
        assert d["succeeded"] is True


class TestAuditStore:
    def test_record_and_read(self, tmp_path):
        cfg = AuditConfig(audit_dir=tmp_path)
        store = AuditStore(cfg)
        e = _entry()
        store.record(e)
        entries = store.read("backup")
        assert len(entries) == 1
        assert entries[0].command == e.command

    def test_read_returns_empty_for_unknown_job(self, tmp_path):
        cfg = AuditConfig(audit_dir=tmp_path)
        store = AuditStore(cfg)
        assert store.read("nonexistent") == []

    def test_max_entries_truncates(self, tmp_path):
        cfg = AuditConfig(audit_dir=tmp_path, max_entries=3)
        store = AuditStore(cfg)
        for i in range(5):
            store.record(_entry(exit_code=i % 2))
        entries = store.read("backup")
        assert len(entries) == 3

    def test_disabled_does_not_write(self, tmp_path):
        cfg = AuditConfig(audit_dir=tmp_path, enabled=False)
        store = AuditStore(cfg)
        store.record(_entry())
        assert store.read("backup") == []

    def test_multiple_jobs_isolated(self, tmp_path):
        cfg = AuditConfig(audit_dir=tmp_path)
        store = AuditStore(cfg)
        store.record(_entry(job_name="jobA"))
        store.record(_entry(job_name="jobB"))
        assert len(store.read("jobA")) == 1
        assert len(store.read("jobB")) == 1
