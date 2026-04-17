"""Tests for cronwrap.snapshot and cronwrap.snapshot_integration."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from cronwrap.snapshot import Snapshot, SnapshotConfig, SnapshotStore
from cronwrap.snapshot_integration import (
    output_changed,
    record_snapshot,
    snapshot_summary,
)


# ---------------------------------------------------------------------------
# SnapshotConfig
# ---------------------------------------------------------------------------

class TestSnapshotConfig:
    def test_defaults(self):
        cfg = SnapshotConfig()
        assert cfg.enabled is False
        assert cfg.algorithm == "sha256"
        assert "cronwrap" in cfg.state_dir

    def test_algorithm_lowercased(self):
        cfg = SnapshotConfig(algorithm="SHA256")
        assert cfg.algorithm == "sha256"

    def test_invalid_algorithm_raises(self):
        with pytest.raises(ValueError, match="Unsupported"):
            SnapshotConfig(algorithm="md999")

    def test_empty_state_dir_raises(self):
        with pytest.raises(ValueError, match="state_dir"):
            SnapshotConfig(state_dir="")

    def test_from_env_defaults(self, monkeypatch):
        monkeypatch.delenv("CRONWRAP_SNAPSHOT_ENABLED", raising=False)
        cfg = SnapshotConfig.from_env()
        assert cfg.enabled is False

    def test_from_env_enabled(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_SNAPSHOT_ENABLED", "true")
        cfg = SnapshotConfig.from_env()
        assert cfg.enabled is True


# ---------------------------------------------------------------------------
# Snapshot dataclass
# ---------------------------------------------------------------------------

def _snap(**kw):
    defaults = dict(job="myjob", digest="abc123", captured_at=1000.0, changed=False)
    defaults.update(kw)
    return Snapshot(**defaults)


class TestSnapshot:
    def test_to_dict_keys(self):
        d = _snap().to_dict()
        assert set(d) == {"job", "digest", "captured_at", "changed"}

    def test_roundtrip(self):
        s = _snap(changed=True)
        assert Snapshot.from_dict(s.to_dict()).changed is True


# ---------------------------------------------------------------------------
# SnapshotStore
# ---------------------------------------------------------------------------

class TestSnapshotStore:
    def test_record_and_load(self, tmp_path):
        cfg = SnapshotConfig(state_dir=str(tmp_path))
        store = SnapshotStore(cfg)
        snap = store.record("job1", "hello world")
        assert not snap.changed  # first record is always "changed"
        # Actually first record has no previous -> changed=True
        assert snap.changed is True

    def test_second_record_unchanged(self, tmp_path):
        cfg = SnapshotConfig(state_dir=str(tmp_path))
        store = SnapshotStore(cfg)
        store.record("job1", "hello")
        snap2 = store.record("job1", "hello")
        assert snap2.changed is False

    def test_second_record_changed(self, tmp_path):
        cfg = SnapshotConfig(state_dir=str(tmp_path))
        store = SnapshotStore(cfg)
        store.record("job1", "hello")
        snap2 = store.record("job1", "world")
        assert snap2.changed is True

    def test_clear_removes_file(self, tmp_path):
        cfg = SnapshotConfig(state_dir=str(tmp_path))
        store = SnapshotStore(cfg)
        store.record("job1", "data")
        store.clear("job1")
        assert store.load("job1") is None


# ---------------------------------------------------------------------------
# Integration helpers
# ---------------------------------------------------------------------------

def _make_result(stdout="", stderr=""):
    r = MagicMock()
    r.stdout = stdout
    r.stderr = stderr
    return r


class TestSnapshotIntegration:
    def test_record_snapshot_returns_snapshot(self, tmp_path):
        cfg = SnapshotConfig(state_dir=str(tmp_path))
        store = SnapshotStore(cfg)
        snap = record_snapshot(store, "j", _make_result(stdout="out"))
        assert snap is not None
        assert snap.job == "j"

    def test_snapshot_summary_changed(self):
        snap = _snap(changed=True, digest="abcdef123456")
        assert "CHANGED" in snapshot_summary(snap)

    def test_snapshot_summary_unchanged(self):
        snap = _snap(changed=False, digest="abcdef123456")
        assert "unchanged" in snapshot_summary(snap)

    def test_snapshot_summary_none(self):
        assert snapshot_summary(None) == "snapshot: no output captured"

    def test_output_changed_true_on_first(self, tmp_path):
        cfg = SnapshotConfig(state_dir=str(tmp_path))
        store = SnapshotStore(cfg)
        assert output_changed(store, "j", _make_result(stdout="x")) is True

    def test_output_changed_false_on_repeat(self, tmp_path):
        cfg = SnapshotConfig(state_dir=str(tmp_path))
        store = SnapshotStore(cfg)
        r = _make_result(stdout="x")
        output_changed(store, "j", r)
        assert output_changed(store, "j", r) is False
