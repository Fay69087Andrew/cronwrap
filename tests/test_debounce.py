"""Tests for cronwrap.debounce."""

from __future__ import annotations

import json
import pytest

from cronwrap.debounce import (
    DebounceConfig,
    DebounceState,
    debounce_summary,
    record_alert,
    should_alert,
)


# ---------------------------------------------------------------------------
# DebounceConfig
# ---------------------------------------------------------------------------

class TestDebounceConfig:
    def test_defaults(self):
        cfg = DebounceConfig()
        assert cfg.window_seconds == 300
        assert cfg.enabled is True
        assert cfg.state_dir != ""

    def test_zero_window_raises(self):
        with pytest.raises(ValueError, match="window_seconds"):
            DebounceConfig(window_seconds=0)

    def test_negative_window_raises(self):
        with pytest.raises(ValueError, match="window_seconds"):
            DebounceConfig(window_seconds=-10)

    def test_empty_state_dir_raises(self):
        with pytest.raises(ValueError, match="state_dir"):
            DebounceConfig(state_dir="")

    def test_from_env_defaults(self, monkeypatch):
        for k in ("CRONWRAP_DEBOUNCE_ENABLED", "CRONWRAP_DEBOUNCE_WINDOW", "CRONWRAP_DEBOUNCE_STATE_DIR"):
            monkeypatch.delenv(k, raising=False)
        cfg = DebounceConfig.from_env()
        assert cfg.window_seconds == 300
        assert cfg.enabled is True

    def test_from_env_custom(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_DEBOUNCE_ENABLED", "false")
        monkeypatch.setenv("CRONWRAP_DEBOUNCE_WINDOW", "60")
        monkeypatch.setenv("CRONWRAP_DEBOUNCE_STATE_DIR", "/tmp/x")
        cfg = DebounceConfig.from_env()
        assert cfg.enabled is False
        assert cfg.window_seconds == 60
        assert cfg.state_dir == "/tmp/x"


# ---------------------------------------------------------------------------
# DebounceState round-trip
# ---------------------------------------------------------------------------

def test_state_roundtrip():
    s = DebounceState(job_id="backup", last_alert_at=1_000_000.0)
    assert DebounceState.from_dict(s.to_dict()).last_alert_at == 1_000_000.0


# ---------------------------------------------------------------------------
# should_alert / record_alert
# ---------------------------------------------------------------------------

def _cfg(tmp_path, window=300, enabled=True):
    return DebounceConfig(window_seconds=window, state_dir=str(tmp_path), enabled=enabled)


def test_should_alert_no_state(tmp_path):
    assert should_alert(_cfg(tmp_path), "job1") is True


def test_should_alert_after_record_within_window(tmp_path):
    cfg = _cfg(tmp_path, window=300)
    now = 1_000_000.0
    record_alert(cfg, "job1", now=now)
    assert should_alert(cfg, "job1", now=now + 100) is False


def test_should_alert_after_window_expires(tmp_path):
    cfg = _cfg(tmp_path, window=300)
    now = 1_000_000.0
    record_alert(cfg, "job1", now=now)
    assert should_alert(cfg, "job1", now=now + 400) is True


def test_should_alert_disabled_always_true(tmp_path):
    cfg = _cfg(tmp_path, enabled=False)
    record_alert(cfg, "job1")
    assert should_alert(cfg, "job1") is True


def test_record_alert_creates_file(tmp_path):
    cfg = _cfg(tmp_path)
    record_alert(cfg, "my-job", now=9999.0)
    files = list(tmp_path.iterdir())
    assert len(files) == 1
    data = json.loads(files[0].read_text())
    assert data["last_alert_at"] == 9999.0


def test_corrupt_state_treated_as_no_state(tmp_path):
    cfg = _cfg(tmp_path, window=300)
    state_file = tmp_path / "job1.json"
    state_file.write_text("not-json")
    assert should_alert(cfg, "job1") is True


# ---------------------------------------------------------------------------
# debounce_summary
# ---------------------------------------------------------------------------

def test_summary_no_previous(tmp_path):
    cfg = _cfg(tmp_path)
    s = debounce_summary(cfg, "job1")
    assert "no previous" in s


def test_summary_within_cooldown(tmp_path):
    cfg = _cfg(tmp_path, window=300)
    now = 1_000_000.0
    record_alert(cfg, "job1", now=now)
    s = debounce_summary(cfg, "job1", now=now + 50)
    assert "250.0s" in s  # remaining


def test_summary_disabled(tmp_path):
    cfg = _cfg(tmp_path, enabled=False)
    s = debounce_summary(cfg, "job1")
    assert "disabled" in s
