"""Tests for cronwrap.digest and cronwrap.digest_integration."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from cronwrap.digest import DigestConfig, DigestEntry, DigestStore
from cronwrap.digest_integration import (
    build_digest_config,
    digest_summary,
    flush_digest,
    record_digest_entry,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _entry(exit_code: int = 0, duration: float = 1.0) -> DigestEntry:
    return DigestEntry(
        job_name="test-job",
        command="echo hi",
        exit_code=exit_code,
        duration=duration,
    )


def _make_run_result(exit_code: int = 0, command: str = "echo hi") -> MagicMock:
    r = MagicMock()
    r.exit_code = exit_code
    r.command = command
    return r


# ---------------------------------------------------------------------------
# DigestConfig
# ---------------------------------------------------------------------------

class TestDigestConfig:
    def test_defaults(self):
        cfg = DigestConfig()
        assert cfg.enabled is False
        assert cfg.max_entries == 100
        assert cfg.job_name == "default"

    def test_zero_max_entries_raises(self):
        with pytest.raises(ValueError, match="max_entries"):
            DigestConfig(max_entries=0)

    def test_negative_max_entries_raises(self):
        with pytest.raises(ValueError, match="max_entries"):
            DigestConfig(max_entries=-1)

    def test_empty_state_dir_raises(self):
        with pytest.raises(ValueError, match="state_dir"):
            DigestConfig(state_dir="")

    def test_empty_job_name_raises(self):
        with pytest.raises(ValueError, match="job_name"):
            DigestConfig(job_name="   ")

    def test_job_name_stripped(self):
        cfg = DigestConfig(job_name="  myjob  ")
        assert cfg.job_name == "myjob"

    def test_from_env(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_DIGEST_ENABLED", "true")
        monkeypatch.setenv("CRONWRAP_DIGEST_MAX_ENTRIES", "50")
        monkeypatch.setenv("CRONWRAP_DIGEST_JOB_NAME", "nightly")
        cfg = DigestConfig.from_env()
        assert cfg.enabled is True
        assert cfg.max_entries == 50
        assert cfg.job_name == "nightly"


# ---------------------------------------------------------------------------
# DigestEntry
# ---------------------------------------------------------------------------

class TestDigestEntry:
    def test_succeeded_on_zero(self):
        assert _entry(0).succeeded() is True

    def test_not_succeeded_on_nonzero(self):
        assert _entry(1).succeeded() is False

    def test_roundtrip_dict(self):
        e = _entry(0, 2.5)
        restored = DigestEntry.from_dict(e.to_dict())
        assert restored.job_name == e.job_name
        assert restored.exit_code == e.exit_code
        assert restored.duration == e.duration

    def test_to_dict_keys(self):
        keys = _entry().to_dict().keys()
        assert {"job_name", "command", "exit_code", "duration", "timestamp"} <= set(keys)


# ---------------------------------------------------------------------------
# DigestStore
# ---------------------------------------------------------------------------

class TestDigestStore:
    def test_empty_summary_on_no_entries(self, tmp_path):
        cfg = DigestConfig(state_dir=str(tmp_path), job_name="j")
        store = DigestStore(cfg)
        s = store.summary()
        assert s["total"] == 0
        assert s["success_rate"] == 0.0

    def test_record_and_retrieve(self, tmp_path):
        cfg = DigestConfig(state_dir=str(tmp_path), job_name="j")
        store = DigestStore(cfg)
        store.record(_entry(0))
        store.record(_entry(1))
        assert len(store.entries()) == 2

    def test_max_entries_enforced(self, tmp_path):
        cfg = DigestConfig(state_dir=str(tmp_path), job_name="j", max_entries=3)
        store = DigestStore(cfg)
        for _ in range(5):
            store.record(_entry())
        assert len(store.entries()) == 3

    def test_clear_removes_file(self, tmp_path):
        cfg = DigestConfig(state_dir=str(tmp_path), job_name="j")
        store = DigestStore(cfg)
        store.record(_entry())
        store.clear()
        assert store.entries() == []

    def test_summary_success_rate(self, tmp_path):
        cfg = DigestConfig(state_dir=str(tmp_path), job_name="j")
        store = DigestStore(cfg)
        store.record(_entry(0))
        store.record(_entry(0))
        store.record(_entry(1))
        s = store.summary()
        assert s["passed"] == 2
        assert s["failed"] == 1
        assert s["success_rate"] == pytest.approx(66.7)


# ---------------------------------------------------------------------------
# Integration helpers
# ---------------------------------------------------------------------------

class TestDigestIntegration:
    def test_record_digest_entry_persists(self, tmp_path):
        cfg = DigestConfig(state_dir=str(tmp_path), job_name="j")
        store = DigestStore(cfg)
        result = _make_run_result(exit_code=0)
        entry = record_digest_entry(store, result, duration=1.23)
        assert entry.exit_code == 0
        assert len(store.entries()) == 1

    def test_digest_summary_string(self, tmp_path):
        cfg = DigestConfig(state_dir=str(tmp_path), job_name="j")
        store = DigestStore(cfg)
        store.record(_entry(0))
        store.record(_entry(1))
        s = digest_summary(store)
        assert "2 runs" in s
        assert "50.0%" in s

    def test_digest_summary_no_entries(self, tmp_path):
        cfg = DigestConfig(state_dir=str(tmp_path), job_name="j")
        store = DigestStore(cfg)
        assert "no entries" in digest_summary(store)

    def test_flush_clears_store(self, tmp_path):
        cfg = DigestConfig(state_dir=str(tmp_path), job_name="j")
        store = DigestStore(cfg)
        store.record(_entry(0))
        result = flush_digest(store)
        assert result["total"] == 1
        assert store.entries() == []
