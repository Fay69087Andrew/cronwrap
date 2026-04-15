"""Tests for cronwrap.checkpoint."""
import json
import time
from pathlib import Path

import pytest

from cronwrap.checkpoint import Checkpoint, CheckpointConfig, CheckpointStore


# ---------------------------------------------------------------------------
# CheckpointConfig
# ---------------------------------------------------------------------------

class TestCheckpointConfig:
    def test_defaults(self):
        cfg = CheckpointConfig()
        assert cfg.enabled is False
        assert cfg.state_dir == "/tmp/cronwrap/checkpoints"
        assert cfg.ttl_seconds == 86400

    def test_zero_ttl_raises(self):
        with pytest.raises(ValueError, match="ttl_seconds"):
            CheckpointConfig(ttl_seconds=0)

    def test_negative_ttl_raises(self):
        with pytest.raises(ValueError, match="ttl_seconds"):
            CheckpointConfig(ttl_seconds=-1)

    def test_empty_state_dir_raises(self):
        with pytest.raises(ValueError, match="state_dir"):
            CheckpointConfig(state_dir="")

    def test_from_env_defaults(self, monkeypatch):
        for k in ("CRONWRAP_CHECKPOINT_ENABLED", "CRONWRAP_CHECKPOINT_DIR", "CRONWRAP_CHECKPOINT_TTL"):
            monkeypatch.delenv(k, raising=False)
        cfg = CheckpointConfig.from_env()
        assert cfg.enabled is False
        assert cfg.ttl_seconds == 86400

    def test_from_env_custom(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_CHECKPOINT_ENABLED", "true")
        monkeypatch.setenv("CRONWRAP_CHECKPOINT_TTL", "3600")
        cfg = CheckpointConfig.from_env()
        assert cfg.enabled is True
        assert cfg.ttl_seconds == 3600


# ---------------------------------------------------------------------------
# Checkpoint dataclass
# ---------------------------------------------------------------------------

def _entry() -> Checkpoint:
    return Checkpoint(job_id="backup", data={"step": 3}, saved_at=1_000_000.0)


class TestCheckpoint:
    def test_roundtrip_dict(self):
        cp = _entry()
        assert Checkpoint.from_dict(cp.to_dict()).data == cp.data

    def test_not_expired_within_ttl(self):
        cp = Checkpoint(job_id="j", saved_at=time.time() - 60)
        assert not cp.is_expired(3600)

    def test_expired_beyond_ttl(self):
        cp = Checkpoint(job_id="j", saved_at=time.time() - 7200)
        assert cp.is_expired(3600)


# ---------------------------------------------------------------------------
# CheckpointStore
# ---------------------------------------------------------------------------

class TestCheckpointStore:
    def test_save_and_load(self, tmp_path):
        cfg = CheckpointConfig(enabled=True, state_dir=str(tmp_path))
        store = CheckpointStore(cfg)
        store.save("myjob", {"offset": 42})
        cp = store.load("myjob")
        assert cp is not None
        assert cp.data["offset"] == 42

    def test_load_returns_none_when_disabled(self, tmp_path):
        cfg = CheckpointConfig(enabled=False, state_dir=str(tmp_path))
        store = CheckpointStore(cfg)
        assert store.load("myjob") is None

    def test_clear_removes_file(self, tmp_path):
        cfg = CheckpointConfig(enabled=True, state_dir=str(tmp_path))
        store = CheckpointStore(cfg)
        store.save("myjob", {"x": 1})
        store.clear("myjob")
        assert store.load("myjob") is None

    def test_load_expired_returns_none(self, tmp_path):
        cfg = CheckpointConfig(enabled=True, state_dir=str(tmp_path), ttl_seconds=1)
        store = CheckpointStore(cfg)
        cp = Checkpoint(job_id="myjob", data={"k": "v"}, saved_at=time.time() - 10)
        (tmp_path / "myjob.json").write_text(json.dumps(cp.to_dict()))
        assert store.load("myjob") is None

    def test_job_id_with_slashes_safe(self, tmp_path):
        cfg = CheckpointConfig(enabled=True, state_dir=str(tmp_path))
        store = CheckpointStore(cfg)
        store.save("a/b/c", {"n": 1})
        cp = store.load("a/b/c")
        assert cp is not None
