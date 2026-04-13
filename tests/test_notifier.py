"""Tests for cronwrap.notifier."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from cronwrap.alerts import AlertConfig
from cronwrap.notifier import NotifierConfig, notify
from cronwrap.retry import RetryResult
from cronwrap.runner import RunResult


def _ok() -> RunResult:
    return RunResult(command="echo hi", returncode=0, stdout="hi", stderr="", duration=0.1)


def _fail() -> RunResult:
    return RunResult(command="false", returncode=1, stdout="", stderr="err", duration=0.2)


def _retry(final: RunResult) -> RetryResult:
    return RetryResult(attempts=[final], final=final)


# ---------------------------------------------------------------------------
# NotifierConfig
# ---------------------------------------------------------------------------

class TestNotifierConfig:
    def test_defaults(self):
        cfg = NotifierConfig()
        assert cfg.enabled is True
        assert cfg.echo is False
        assert cfg.failure_only is True
        assert isinstance(cfg.alert, AlertConfig)

    def test_from_env_disabled(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_NOTIFY_ENABLED", "false")
        cfg = NotifierConfig.from_env()
        assert cfg.enabled is False

    def test_from_env_echo(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_NOTIFY_ECHO", "true")
        cfg = NotifierConfig.from_env()
        assert cfg.echo is True

    def test_from_env_failure_only_false(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_NOTIFY_FAILURE_ONLY", "false")
        cfg = NotifierConfig.from_env()
        assert cfg.failure_only is False


# ---------------------------------------------------------------------------
# notify()
# ---------------------------------------------------------------------------

class TestNotify:
    def test_returns_false_when_disabled(self):
        cfg = NotifierConfig(enabled=False)
        assert notify(_fail(), None, cfg) is False

    def test_returns_false_on_success_when_failure_only(self):
        cfg = NotifierConfig(failure_only=True)
        assert notify(_ok(), None, cfg) is False

    def test_sends_when_success_and_not_failure_only(self, capsys):
        cfg = NotifierConfig(failure_only=False, echo=True)
        sent = notify(_ok(), None, cfg)
        assert sent is True
        captured = capsys.readouterr()
        assert "echo hi" in captured.out

    def test_echo_prints_subject_and_body(self, capsys):
        cfg = NotifierConfig(echo=True, failure_only=False)
        notify(_fail(), _retry(_fail()), cfg)
        captured = capsys.readouterr()
        assert "[cronwrap]" in captured.out

    def test_calls_send_alert_when_smtp_configured(self):
        alert_cfg = AlertConfig(
            smtp_host="smtp.example.com",
            to_address="ops@example.com",
            from_address="cron@example.com",
        )
        cfg = NotifierConfig(failure_only=False, alert=alert_cfg)
        with patch("cronwrap.notifier.send_alert") as mock_send:
            result = notify(_fail(), None, cfg)
        mock_send.assert_called_once()
        assert result is True

    def test_no_smtp_no_echo_returns_false(self):
        cfg = NotifierConfig(echo=False, failure_only=False)
        assert notify(_fail(), None, cfg) is False
