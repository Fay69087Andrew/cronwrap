"""Tests for cronwrap.healthcheck."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from cronwrap.healthcheck import HealthcheckConfig, send_healthcheck
from cronwrap.runner import RunResult


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _result(exit_code: int = 0) -> RunResult:
    return RunResult(command="echo hi", exit_code=exit_code, stdout="hi", stderr="")


# ---------------------------------------------------------------------------
# HealthcheckConfig
# ---------------------------------------------------------------------------

class TestHealthcheckConfig:
    def test_defaults(self):
        cfg = HealthcheckConfig()
        assert cfg.ping_url is None
        assert cfg.ping_url_failure is None
        assert cfg.timeout_seconds == 10
        assert cfg.enabled is True

    def test_zero_timeout_raises(self):
        with pytest.raises(ValueError, match="positive"):
            HealthcheckConfig(timeout_seconds=0)

    def test_negative_timeout_raises(self):
        with pytest.raises(ValueError):
            HealthcheckConfig(timeout_seconds=-5)

    def test_from_env_defaults(self, monkeypatch):
        for key in ("CRONWRAP_HC_URL", "CRONWRAP_HC_FAIL_URL",
                    "CRONWRAP_HC_TIMEOUT", "CRONWRAP_HC_ENABLED"):
            monkeypatch.delenv(key, raising=False)
        cfg = HealthcheckConfig.from_env()
        assert cfg.ping_url is None
        assert cfg.enabled is True
        assert cfg.timeout_seconds == 10

    def test_from_env_custom(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_HC_URL", "https://hc.example.com/abc")
        monkeypatch.setenv("CRONWRAP_HC_FAIL_URL", "https://hc.example.com/abc/fail")
        monkeypatch.setenv("CRONWRAP_HC_TIMEOUT", "5")
        monkeypatch.setenv("CRONWRAP_HC_ENABLED", "1")
        cfg = HealthcheckConfig.from_env()
        assert cfg.ping_url == "https://hc.example.com/abc"
        assert cfg.ping_url_failure == "https://hc.example.com/abc/fail"
        assert cfg.timeout_seconds == 5
        assert cfg.enabled is True

    def test_from_env_disabled(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_HC_ENABLED", "false")
        cfg = HealthcheckConfig.from_env()
        assert cfg.enabled is False


# ---------------------------------------------------------------------------
# send_healthcheck
# ---------------------------------------------------------------------------

class TestSendHealthcheck:
    def test_no_url_returns_false(self):
        cfg = HealthcheckConfig(ping_url=None)
        assert send_healthcheck(_result(0), cfg) is False

    def test_disabled_returns_false(self):
        cfg = HealthcheckConfig(ping_url="https://hc.example.com/x", enabled=False)
        assert send_healthcheck(_result(0), cfg) is False

    def test_success_pings_base_url(self):
        cfg = HealthcheckConfig(ping_url="https://hc.example.com/uuid")
        with patch("cronwrap.healthcheck._ping", return_value=True) as mock_ping:
            result = send_healthcheck(_result(0), cfg)
        mock_ping.assert_called_once_with("https://hc.example.com/uuid", 10)
        assert result is True

    def test_failure_pings_fail_url_default(self):
        cfg = HealthcheckConfig(ping_url="https://hc.example.com/uuid")
        with patch("cronwrap.healthcheck._ping", return_value=True) as mock_ping:
            send_healthcheck(_result(1), cfg)
        mock_ping.assert_called_once_with("https://hc.example.com/uuid/fail", 10)

    def test_failure_pings_explicit_fail_url(self):
        cfg = HealthcheckConfig(
            ping_url="https://hc.example.com/uuid",
            ping_url_failure="https://hc.example.com/uuid/fail-custom",
        )
        with patch("cronwrap.healthcheck._ping", return_value=True) as mock_ping:
            send_healthcheck(_result(1), cfg)
        mock_ping.assert_called_once_with("https://hc.example.com/uuid/fail-custom", 10)

    def test_network_error_returns_false(self):
        import urllib.error
        cfg = HealthcheckConfig(ping_url="https://hc.example.com/uuid")
        with patch(
            "cronwrap.healthcheck.urllib.request.urlopen",
            side_effect=urllib.error.URLError("unreachable"),
        ):
            result = send_healthcheck(_result(0), cfg)
        assert result is False
