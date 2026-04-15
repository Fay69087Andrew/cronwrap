"""Tests for cronwrap.heartbeat."""

from __future__ import annotations

import pytest

from cronwrap.heartbeat import HeartbeatConfig, HeartbeatWorker


# ---------------------------------------------------------------------------
# HeartbeatConfig
# ---------------------------------------------------------------------------

class TestHeartbeatConfig:
    def test_defaults(self):
        cfg = HeartbeatConfig()
        assert cfg.url == ""
        assert cfg.interval == 60.0
        assert cfg.timeout == 10.0
        assert cfg.enabled is True

    def test_zero_interval_raises(self):
        with pytest.raises(ValueError, match="interval"):
            HeartbeatConfig(interval=0)

    def test_negative_interval_raises(self):
        with pytest.raises(ValueError, match="interval"):
            HeartbeatConfig(interval=-5)

    def test_zero_timeout_raises(self):
        with pytest.raises(ValueError, match="timeout"):
            HeartbeatConfig(timeout=0)

    def test_from_env_defaults(self, monkeypatch):
        for key in ("CRONWRAP_HEARTBEAT_URL", "CRONWRAP_HEARTBEAT_INTERVAL",
                    "CRONWRAP_HEARTBEAT_TIMEOUT", "CRONWRAP_HEARTBEAT_ENABLED"):
            monkeypatch.delenv(key, raising=False)
        cfg = HeartbeatConfig.from_env()
        assert cfg.url == ""
        assert cfg.interval == 60.0
        assert cfg.enabled is True

    def test_from_env_custom(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_HEARTBEAT_URL", "https://example.com/ping")
        monkeypatch.setenv("CRONWRAP_HEARTBEAT_INTERVAL", "30")
        monkeypatch.setenv("CRONWRAP_HEARTBEAT_ENABLED", "false")
        cfg = HeartbeatConfig.from_env()
        assert cfg.url == "https://example.com/ping"
        assert cfg.interval == 30.0
        assert cfg.enabled is False


# ---------------------------------------------------------------------------
# HeartbeatWorker
# ---------------------------------------------------------------------------

def _make_worker(url="https://ping.example.com", interval=0.05, ping_fn=None):
    cfg = HeartbeatConfig(url=url, interval=interval, timeout=5.0)
    return HeartbeatWorker(cfg, ping_fn=ping_fn)


class TestHeartbeatWorker:
    def test_start_stop_no_url_does_nothing(self):
        cfg = HeartbeatConfig(url="", interval=0.05)
        w = HeartbeatWorker(cfg)
        w.start()
        w.stop()
        assert w.ping_count == 0

    def test_disabled_does_not_ping(self):
        calls = []
        cfg = HeartbeatConfig(url="https://x.com", interval=0.05, enabled=False)
        w = HeartbeatWorker(cfg, ping_fn=lambda u, t: calls.append(u))
        w.start()
        import time; time.sleep(0.12)
        w.stop()
        assert len(calls) == 0

    def test_pings_while_running(self):
        calls = []
        w = _make_worker(ping_fn=lambda u, t: calls.append(u))
        w.start()
        import time; time.sleep(0.18)
        w.stop()
        assert w.ping_count >= 2

    def test_records_last_error_on_exception(self):
        def bad_ping(u, t):
            raise RuntimeError("network down")
        w = _make_worker(ping_fn=bad_ping)
        w.start()
        import time; time.sleep(0.12)
        w.stop()
        assert w.last_error == "network down"

    def test_summary_keys(self):
        w = _make_worker()
        s = w.summary()
        assert set(s) == {"url", "interval", "ping_count", "last_error"}
