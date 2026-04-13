"""Tests for cronwrap.webhook."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from cronwrap.runner import RunResult
from cronwrap.webhook import WebhookConfig, _build_payload, send_webhook


def _result(exit_code: int = 0, stdout: str = "", stderr: str = "") -> RunResult:
    return RunResult(
        command="echo hi",
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        duration_seconds=0.5,
    )


class TestWebhookConfig:
    def test_defaults(self):
        cfg = WebhookConfig()
        assert cfg.url is None
        assert cfg.on_failure_only is True
        assert cfg.timeout_seconds == 10
        assert cfg.extra_headers == {}

    def test_zero_timeout_raises(self):
        with pytest.raises(ValueError):
            WebhookConfig(url="http://example.com", timeout_seconds=0)

    def test_negative_timeout_raises(self):
        with pytest.raises(ValueError):
            WebhookConfig(url="http://example.com", timeout_seconds=-5)

    def test_from_env_defaults(self, monkeypatch):
        monkeypatch.delenv("CRONWRAP_WEBHOOK_URL", raising=False)
        monkeypatch.delenv("CRONWRAP_WEBHOOK_ON_FAILURE", raising=False)
        monkeypatch.delenv("CRONWRAP_WEBHOOK_TIMEOUT", raising=False)
        cfg = WebhookConfig.from_env()
        assert cfg.url is None
        assert cfg.on_failure_only is True
        assert cfg.timeout_seconds == 10

    def test_from_env_custom(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_WEBHOOK_URL", "http://hook.example.com/notify")
        monkeypatch.setenv("CRONWRAP_WEBHOOK_ON_FAILURE", "0")
        monkeypatch.setenv("CRONWRAP_WEBHOOK_TIMEOUT", "5")
        cfg = WebhookConfig.from_env()
        assert cfg.url == "http://hook.example.com/notify"
        assert cfg.on_failure_only is False
        assert cfg.timeout_seconds == 5


class TestBuildPayload:
    def test_payload_keys(self):
        r = _result(exit_code=1, stdout="out", stderr="err")
        data = json.loads(_build_payload(r))
        assert set(data.keys()) == {
            "command", "exit_code", "success", "stdout", "stderr", "duration_seconds"
        }

    def test_payload_values(self):
        r = _result(exit_code=0, stdout="hello")
        data = json.loads(_build_payload(r))
        assert data["success"] is True
        assert data["stdout"] == "hello"
        assert data["exit_code"] == 0


class TestSendWebhook:
    def test_skipped_when_no_url(self):
        cfg = WebhookConfig(url=None)
        assert send_webhook(_result(), cfg) is False

    def test_skipped_on_success_when_failure_only(self):
        cfg = WebhookConfig(url="http://example.com", on_failure_only=True)
        assert send_webhook(_result(exit_code=0), cfg) is False

    def test_sent_on_failure_when_failure_only(self):
        cfg = WebhookConfig(url="http://example.com", on_failure_only=True)
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.status = 200
        with patch("urllib.request.urlopen", return_value=mock_resp):
            assert send_webhook(_result(exit_code=1), cfg) is True

    def test_sent_on_success_when_not_failure_only(self):
        cfg = WebhookConfig(url="http://example.com", on_failure_only=False)
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.status = 204
        with patch("urllib.request.urlopen", return_value=mock_resp):
            assert send_webhook(_result(exit_code=0), cfg) is True

    def test_returns_false_on_url_error(self):
        import urllib.error
        cfg = WebhookConfig(url="http://bad.example.com", on_failure_only=False)
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("fail")):
            assert send_webhook(_result(), cfg) is False
