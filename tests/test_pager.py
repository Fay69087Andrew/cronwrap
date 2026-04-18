"""Tests for cronwrap.pager."""
import pytest
from cronwrap.pager import PagerConfig, PagerEvent, send_page


class TestPagerConfig:
    def test_defaults(self):
        cfg = PagerConfig()
        assert cfg.enabled is False
        assert cfg.routing_key == ""
        assert cfg.source == "cronwrap"
        assert cfg.severity == "error"
        assert cfg.timeout == 10

    def test_severity_lowercased(self):
        cfg = PagerConfig(severity="CRITICAL")
        assert cfg.severity == "critical"

    def test_invalid_severity_raises(self):
        with pytest.raises(ValueError, match="severity"):
            PagerConfig(severity="fatal")

    def test_zero_timeout_raises(self):
        with pytest.raises(ValueError, match="timeout"):
            PagerConfig(timeout=0)

    def test_negative_timeout_raises(self):
        with pytest.raises(ValueError, match="timeout"):
            PagerConfig(timeout=-1)

    def test_enabled_without_routing_key_raises(self):
        with pytest.raises(ValueError, match="routing_key"):
            PagerConfig(enabled=True, routing_key="")

    def test_enabled_with_routing_key_ok(self):
        cfg = PagerConfig(enabled=True, routing_key="abc123")
        assert cfg.enabled is True

    def test_from_env_defaults(self, monkeypatch):
        for k in ["CRONWRAP_PAGER_ENABLED", "CRONWRAP_PAGER_ROUTING_KEY",
                  "CRONWRAP_PAGER_SOURCE", "CRONWRAP_PAGER_SEVERITY",
                  "CRONWRAP_PAGER_TIMEOUT"]:
            monkeypatch.delenv(k, raising=False)
        cfg = PagerConfig.from_env()
        assert cfg.enabled is False

    def test_from_env_custom(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_PAGER_ENABLED", "true")
        monkeypatch.setenv("CRONWRAP_PAGER_ROUTING_KEY", "key-xyz")
        monkeypatch.setenv("CRONWRAP_PAGER_SEVERITY", "critical")
        monkeypatch.setenv("CRONWRAP_PAGER_TIMEOUT", "5")
        cfg = PagerConfig.from_env()
        assert cfg.enabled is True
        assert cfg.routing_key == "key-xyz"
        assert cfg.severity == "critical"
        assert cfg.timeout == 5


class TestPagerEvent:
    def test_to_payload_structure(self):
        ev = PagerEvent(summary="boom", source="cronwrap", severity="error")
        payload = ev.to_payload("rk-123")
        assert payload["routing_key"] == "rk-123"
        assert payload["event_action"] == "trigger"
        assert payload["payload"]["summary"] == "boom"
        assert payload["payload"]["severity"] == "error"

    def test_custom_details_included(self):
        ev = PagerEvent("s", "src", "info", custom_details={"k": "v"})
        payload = ev.to_payload("rk")
        assert payload["payload"]["custom_details"] == {"k": "v"}


class TestSendPage:
    def test_returns_none_when_disabled(self):
        cfg = PagerConfig(enabled=False)
        ev = PagerEvent("s", "src", "error")
        assert send_page(cfg, ev) is None
