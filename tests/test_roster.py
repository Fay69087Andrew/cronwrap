"""Tests for cronwrap.roster and cronwrap.roster_integration."""
from __future__ import annotations

import time
from pathlib import Path

import pytest

from cronwrap.roster import RosterConfig, RosterEntry, RosterStore
from cronwrap.roster_integration import ensure_registered, roster_summary


# ---------------------------------------------------------------------------
# RosterConfig
# ---------------------------------------------------------------------------

class TestRosterConfig:
    def test_defaults(self):
        cfg = RosterConfig()
        assert cfg.enabled is True
        assert cfg.max_jobs == 256
        assert cfg.state_dir == "/tmp/cronwrap/roster"

    def test_zero_max_jobs_raises(self):
        with pytest.raises(ValueError, match="max_jobs"):
            RosterConfig(max_jobs=0)

    def test_negative_max_jobs_raises(self):
        with pytest.raises(ValueError, match="max_jobs"):
            RosterConfig(max_jobs=-1)

    def test_empty_state_dir_raises(self):
        with pytest.raises(ValueError, match="state_dir"):
            RosterConfig(state_dir="")

    def test_from_env_defaults(self, monkeypatch):
        for k in ("CRONWRAP_ROSTER_ENABLED", "CRONWRAP_ROSTER_STATE_DIR", "CRONWRAP_ROSTER_MAX_JOBS"):
            monkeypatch.delenv(k, raising=False)
        cfg = RosterConfig.from_env()
        assert cfg.enabled is True
        assert cfg.max_jobs == 256

    def test_from_env_disabled(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_ROSTER_ENABLED", "false")
        cfg = RosterConfig.from_env()
        assert cfg.enabled is False


# ---------------------------------------------------------------------------
# RosterEntry
# ---------------------------------------------------------------------------

def _entry() -> RosterEntry:
    return RosterEntry(job_id="backup", command="/usr/bin/backup.sh", tags={"env": "prod"})


class TestRosterEntry:
    def test_roundtrip_dict(self):
        e = _entry()
        assert RosterEntry.from_dict(e.to_dict()).job_id == e.job_id

    def test_to_dict_keys(self):
        d = _entry().to_dict()
        assert {"job_id", "command", "registered_at", "last_seen", "tags"} == set(d)

    def test_last_seen_defaults_none(self):
        assert _entry().last_seen is None


# ---------------------------------------------------------------------------
# RosterStore
# ---------------------------------------------------------------------------

def _store(tmp_path: Path) -> RosterStore:
    cfg = RosterConfig(state_dir=str(tmp_path / "roster"))
    return RosterStore(cfg)


class TestRosterStore:
    def test_register_and_get(self, tmp_path):
        s = _store(tmp_path)
        s.register(_entry())
        e = s.get("backup")
        assert e is not None
        assert e.command == "/usr/bin/backup.sh"

    def test_get_missing_returns_none(self, tmp_path):
        assert _store(tmp_path).get("nope") is None

    def test_deregister(self, tmp_path):
        s = _store(tmp_path)
        s.register(_entry())
        s.deregister("backup")
        assert s.get("backup") is None

    def test_list_jobs(self, tmp_path):
        s = _store(tmp_path)
        s.register(_entry())
        assert len(s.list_jobs()) == 1

    def test_max_jobs_enforced(self, tmp_path):
        cfg = RosterConfig(state_dir=str(tmp_path / "r"), max_jobs=1)
        s = RosterStore(cfg)
        s.register(RosterEntry(job_id="a", command="a"))
        with pytest.raises(RuntimeError, match="full"):
            s.register(RosterEntry(job_id="b", command="b"))

    def test_touch_updates_last_seen(self, tmp_path):
        s = _store(tmp_path)
        s.register(_entry())
        s.touch("backup")
        e = s.get("backup")
        assert e is not None and e.last_seen is not None

    def test_disabled_store_skips_write(self, tmp_path):
        cfg = RosterConfig(enabled=False, state_dir=str(tmp_path / "r"))
        s = RosterStore(cfg)
        s.register(_entry())
        assert s.get("backup") is None

    def test_ensure_registered_idempotent(self, tmp_path):
        s = _store(tmp_path)
        ensure_registered(s, "backup", "/usr/bin/backup.sh")
        ensure_registered(s, "backup", "/usr/bin/backup.sh")
        assert len(s.list_jobs()) == 1

    def test_roster_summary_empty(self, tmp_path):
        assert "no jobs" in roster_summary(_store(tmp_path))

    def test_roster_summary_lists_jobs(self, tmp_path):
        s = _store(tmp_path)
        s.register(_entry())
        summary = roster_summary(s)
        assert "backup" in summary
