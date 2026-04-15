"""Tests for cronwrap.runbook."""
import pytest
from cronwrap.runbook import RunbookConfig, runbook_summary, format_runbook_line


class TestRunbookConfig:
    def test_defaults(self):
        cfg = RunbookConfig()
        assert cfg.url is None
        assert cfg.title == "Runbook"
        assert cfg.enabled is True

    def test_valid_url_accepted(self):
        cfg = RunbookConfig(url="https://wiki.example.com/runbook")
        assert cfg.url == "https://wiki.example.com/runbook"

    def test_http_url_accepted(self):
        cfg = RunbookConfig(url="http://internal/runbook")
        assert cfg.url == "http://internal/runbook"

    def test_invalid_url_raises(self):
        with pytest.raises(ValueError, match="http"):
            RunbookConfig(url="ftp://bad.example.com")

    def test_title_stripped(self):
        cfg = RunbookConfig(title="  My Guide  ")
        assert cfg.title == "My Guide"

    def test_title_too_long_raises(self):
        with pytest.raises(ValueError, match="title"):
            RunbookConfig(title="x" * 121)

    def test_url_too_long_raises(self):
        with pytest.raises(ValueError, match="url"):
            RunbookConfig(url="https://x.com/" + "a" * 2048)

    def test_url_stripped(self):
        cfg = RunbookConfig(url="  https://example.com/rb  ")
        assert cfg.url == "https://example.com/rb"

    def test_from_env_defaults(self, monkeypatch):
        for key in ("CRONWRAP_RUNBOOK_URL", "CRONWRAP_RUNBOOK_TITLE", "CRONWRAP_RUNBOOK_ENABLED"):
            monkeypatch.delenv(key, raising=False)
        cfg = RunbookConfig.from_env()
        assert cfg.url is None
        assert cfg.title == "Runbook"
        assert cfg.enabled is True

    def test_from_env_custom(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_RUNBOOK_URL", "https://docs.example.com")
        monkeypatch.setenv("CRONWRAP_RUNBOOK_TITLE", "Ops Guide")
        monkeypatch.setenv("CRONWRAP_RUNBOOK_ENABLED", "true")
        cfg = RunbookConfig.from_env()
        assert cfg.url == "https://docs.example.com"
        assert cfg.title == "Ops Guide"
        assert cfg.enabled is True

    def test_from_env_disabled(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_RUNBOOK_ENABLED", "false")
        cfg = RunbookConfig.from_env()
        assert cfg.enabled is False

    def test_from_env_disabled_zero(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_RUNBOOK_ENABLED", "0")
        cfg = RunbookConfig.from_env()
        assert cfg.enabled is False


class TestRunbookSummary:
    def test_not_configured_when_no_url(self):
        cfg = RunbookConfig()
        assert runbook_summary(cfg) == "runbook: not configured"

    def test_not_configured_when_disabled(self):
        cfg = RunbookConfig(url="https://example.com", enabled=False)
        assert runbook_summary(cfg) == "runbook: not configured"

    def test_shows_title_and_url(self):
        cfg = RunbookConfig(url="https://example.com/rb", title="Ops")
        assert runbook_summary(cfg) == "runbook: Ops -> https://example.com/rb"


class TestFormatRunbookLine:
    def test_none_when_no_url(self):
        assert format_runbook_line(RunbookConfig()) is None

    def test_none_when_disabled(self):
        cfg = RunbookConfig(url="https://example.com", enabled=False)
        assert format_runbook_line(cfg) is None

    def test_markdown_link(self):
        cfg = RunbookConfig(url="https://example.com/rb", title="Guide")
        assert format_runbook_line(cfg) == "[Guide](https://example.com/rb)"
