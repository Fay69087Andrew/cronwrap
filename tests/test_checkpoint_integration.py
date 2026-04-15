"""Tests for cronwrap.checkpoint_integration."""
import pytest

from cronwrap.checkpoint import CheckpointConfig, CheckpointStore
from cronwrap.checkpoint_integration import (
    build_checkpoint_store,
    checkpoint_summary,
    commit_checkpoint,
    finalize_checkpoint,
    resume_or_start,
)
from cronwrap.runner import RunResult


def _store(tmp_path):
    cfg = CheckpointConfig(enabled=True, state_dir=str(tmp_path))
    return CheckpointStore(cfg)


def _result(exit_code: int) -> RunResult:
    return RunResult(command="echo hi", exit_code=exit_code, stdout=b"", stderr=b"", duration=0.1)


class TestResumeOrStart:
    def test_returns_none_when_no_checkpoint(self, tmp_path):
        store = _store(tmp_path)
        assert resume_or_start(store, "job1") is None

    def test_returns_data_when_checkpoint_exists(self, tmp_path):
        store = _store(tmp_path)
        store.save("job1", {"step": 5})
        data = resume_or_start(store, "job1")
        assert data == {"step": 5}


class TestCommitCheckpoint:
    def test_saves_and_returns_checkpoint(self, tmp_path):
        store = _store(tmp_path)
        cp = commit_checkpoint(store, "job2", {"progress": 0.5})
        assert cp.data["progress"] == 0.5
        loaded = store.load("job2")
        assert loaded is not None


class TestFinalizeCheckpoint:
    def test_clears_on_success(self, tmp_path):
        store = _store(tmp_path)
        store.save("job3", {"x": 1})
        finalize_checkpoint(store, "job3", _result(0))
        assert store.load("job3") is None

    def test_keeps_on_failure(self, tmp_path):
        store = _store(tmp_path)
        store.save("job3", {"x": 1})
        finalize_checkpoint(store, "job3", _result(1))
        assert store.load("job3") is not None


class TestCheckpointSummary:
    def test_none_checkpoint(self):
        assert checkpoint_summary(None) == "checkpoint: none"

    def test_with_checkpoint(self, tmp_path):
        store = _store(tmp_path)
        cp = store.save("job4", {"a": 1, "b": 2})
        summary = checkpoint_summary(cp)
        assert "job4" in summary
        assert "a" in summary
        assert "b" in summary

    def test_empty_data_checkpoint(self, tmp_path):
        store = _store(tmp_path)
        cp = store.save("job5", {})
        summary = checkpoint_summary(cp)
        assert "(empty)" in summary


class TestBuildCheckpointStore:
    def test_returns_store_from_env(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_CHECKPOINT_ENABLED", "false")
        store = build_checkpoint_store()
        assert isinstance(store, CheckpointStore)
