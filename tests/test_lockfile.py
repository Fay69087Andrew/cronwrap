"""Tests for cronwrap.lockfile."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from cronwrap.lockfile import LockConfig, LockFile, LockFileError


# ---------------------------------------------------------------------------
# LockConfig
# ---------------------------------------------------------------------------

class TestLockConfig:
    def test_defaults(self):
        cfg = LockConfig()
        assert cfg.lock_dir == "/tmp/cronwrap"
        assert cfg.enabled is True

    def test_from_env_disabled(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_LOCK_ENABLED", "false")
        cfg = LockConfig.from_env()
        assert cfg.enabled is False

    def test_from_env_custom_dir(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_LOCK_DIR", "/var/run/cronwrap")
        cfg = LockConfig.from_env()
        assert cfg.lock_dir == "/var/run/cronwrap"


# ---------------------------------------------------------------------------
# LockFile helpers
# ---------------------------------------------------------------------------

def _cfg(tmp_path: Path) -> LockConfig:
    return LockConfig(lock_dir=str(tmp_path))


# ---------------------------------------------------------------------------
# LockFile
# ---------------------------------------------------------------------------

class TestLockFile:
    def test_acquire_creates_file(self, tmp_path):
        lf = LockFile("backup", config=_cfg(tmp_path))
        lf.acquire()
        lock = tmp_path / "backup.lock"
        assert lock.exists()
        assert lock.read_text().strip() == str(os.getpid())
        lf.release()

    def test_release_removes_file(self, tmp_path):
        lf = LockFile("backup", config=_cfg(tmp_path))
        lf.acquire()
        lf.release()
        assert not (tmp_path / "backup.lock").exists()

    def test_double_acquire_raises(self, tmp_path):
        lf1 = LockFile("job", config=_cfg(tmp_path))
        lf2 = LockFile("job", config=_cfg(tmp_path))
        lf1.acquire()
        with pytest.raises(LockFileError, match="already running"):
            lf2.acquire()
        lf1.release()

    def test_context_manager_releases_on_success(self, tmp_path):
        lock_path = tmp_path / "myjob.lock"
        with LockFile("myjob", config=_cfg(tmp_path)):
            assert lock_path.exists()
        assert not lock_path.exists()

    def test_context_manager_releases_on_exception(self, tmp_path):
        lock_path = tmp_path / "myjob.lock"
        with pytest.raises(RuntimeError):
            with LockFile("myjob", config=_cfg(tmp_path)):
                assert lock_path.exists()
                raise RuntimeError("boom")
        assert not lock_path.exists()

    def test_disabled_lock_does_not_create_file(self, tmp_path):
        cfg = LockConfig(lock_dir=str(tmp_path), enabled=False)
        lf = LockFile("noop", config=cfg)
        lf.acquire()
        assert not (tmp_path / "noop.lock").exists()
        lf.release()  # should not raise

    def test_slash_in_name_is_sanitised(self, tmp_path):
        lf = LockFile("path/to/job", config=_cfg(tmp_path))
        lf.acquire()
        assert (tmp_path / "path_to_job.lock").exists()
        lf.release()
