"""Tests for cronwrap.concurrency and cronwrap.concurrency_integration."""
from __future__ import annotations

import os
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cronwrap.concurrency import (
    ConcurrencyConfig,
    ConcurrencyLimitError,
    acquire_slot,
    concurrency_summary,
    release_slot,
)
from cronwrap.concurrency_integration import (
    check_concurrency_or_abort,
    run_with_concurrency_guard,
)
from cronwrap.runner import RunResult


# ---------------------------------------------------------------------------
# ConcurrencyConfig
# ---------------------------------------------------------------------------

class TestConcurrencyConfig:
    def test_defaults(self):
        cfg = ConcurrencyConfig()
        assert cfg.max_instances == 1
        assert cfg.state_dir == "/tmp/cronwrap/concurrency"
        assert cfg.enabled is True

    def test_zero_max_instances_raises(self):
        with pytest.raises(ValueError, match="max_instances"):
            ConcurrencyConfig(max_instances=0)

    def test_negative_max_instances_raises(self):
        with pytest.raises(ValueError):
            ConcurrencyConfig(max_instances=-1)

    def test_empty_state_dir_raises(self):
        with pytest.raises(ValueError, match="state_dir"):
            ConcurrencyConfig(state_dir="")

    def test_from_env_defaults(self, monkeypatch):
        monkeypatch.delenv("CRONWRAP_CONCURRENCY_ENABLED", raising=False)
        monkeypatch.delenv("CRONWRAP_MAX_INSTANCES", raising=False)
        monkeypatch.delenv("CRONWRAP_CONCURRENCY_DIR", raising=False)
        cfg = ConcurrencyConfig.from_env()
        assert cfg.max_instances == 1
        assert cfg.enabled is True

    def test_from_env_custom(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_MAX_INSTANCES", "3")
        monkeypatch.setenv("CRONWRAP_CONCURRENCY_ENABLED", "false")
        monkeypatch.setenv("CRONWRAP_CONCURRENCY_DIR", "/var/cronwrap")
        cfg = ConcurrencyConfig.from_env()
        assert cfg.max_instances == 3
        assert cfg.enabled is False
        assert cfg.state_dir == "/var/cronwrap"


# ---------------------------------------------------------------------------
# acquire_slot / release_slot
# ---------------------------------------------------------------------------

def test_acquire_slot_creates_file(tmp_path):
    cfg = ConcurrencyConfig(state_dir=str(tmp_path))
    slot = acquire_slot(cfg, "myjob")
    assert slot is not None
    assert slot.exists()
    release_slot(slot)
    assert not slot.exists()


def test_acquire_slot_disabled_returns_devnull(tmp_path):
    cfg = ConcurrencyConfig(state_dir=str(tmp_path), enabled=False)
    slot = acquire_slot(cfg, "myjob")
    assert slot == Path(os.devnull)
    release_slot(slot)  # should not raise


def test_acquire_slot_limit_reached(tmp_path):
    cfg = ConcurrencyConfig(max_instances=1, state_dir=str(tmp_path))
    slot1 = acquire_slot(cfg, "myjob")
    assert slot1 is not None
    # Simulate a second process by writing a slot file with the current PID
    # (acquire_slot already wrote one; limit=1 so next should fail)
    slot2 = acquire_slot(cfg, "myjob")
    assert slot2 is None
    release_slot(slot1)


# ---------------------------------------------------------------------------
# concurrency_summary
# ---------------------------------------------------------------------------

def test_concurrency_summary_keys(tmp_path):
    cfg = ConcurrencyConfig(state_dir=str(tmp_path))
    summary = concurrency_summary(cfg, "backup")
    assert summary["job_name"] == "backup"
    assert summary["max_instances"] == 1
    assert "active_instances" in summary
    assert "enabled" in summary


# ---------------------------------------------------------------------------
# run_with_concurrency_guard
# ---------------------------------------------------------------------------

def _ok_result() -> RunResult:
    return RunResult(command="echo hi", returncode=0, stdout=b"hi", stderr=b"")


def test_run_with_concurrency_guard_success(tmp_path):
    cfg = ConcurrencyConfig(state_dir=str(tmp_path))
    result, summary = run_with_concurrency_guard(cfg, "job1", _ok_result)
    assert result.success
    assert summary["job_name"] == "job1"


def test_run_with_concurrency_guard_raises_when_limit_reached(tmp_path):
    cfg = ConcurrencyConfig(max_instances=1, state_dir=str(tmp_path))
    slot = acquire_slot(cfg, "job2")
    with pytest.raises(ConcurrencyLimitError, match="job2"):
        run_with_concurrency_guard(cfg, "job2", _ok_result)
    release_slot(slot)


def test_slot_released_even_on_exception(tmp_path):
    cfg = ConcurrencyConfig(state_dir=str(tmp_path))

    def boom() -> RunResult:
        raise RuntimeError("oops")

    with pytest.raises(RuntimeError):
        run_with_concurrency_guard(cfg, "job3", boom)

    # After the exception the slot must be released so a new one can be acquired
    slot = acquire_slot(cfg, "job3")
    assert slot is not None
    release_slot(slot)


# ---------------------------------------------------------------------------
# check_concurrency_or_abort
# ---------------------------------------------------------------------------

def test_check_concurrency_or_abort_passes_when_free(tmp_path):
    cfg = ConcurrencyConfig(state_dir=str(tmp_path))
    check_concurrency_or_abort(cfg, "jobX")  # should not raise


def test_check_concurrency_or_abort_exits_when_full(tmp_path):
    cfg = ConcurrencyConfig(max_instances=1, state_dir=str(tmp_path))
    slot = acquire_slot(cfg, "jobY")
    with pytest.raises(SystemExit):
        check_concurrency_or_abort(cfg, "jobY")
    release_slot(slot)
