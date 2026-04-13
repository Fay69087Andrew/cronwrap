"""Tests for cronwrap.redactor."""

import pytest

from cronwrap.redactor import RedactorConfig, redact, _REDACTED


# ---------------------------------------------------------------------------
# RedactorConfig
# ---------------------------------------------------------------------------

class TestRedactorConfig:
    def test_defaults(self):
        cfg = RedactorConfig()
        assert cfg.enabled is True
        assert cfg.extra_patterns == []
        assert cfg.placeholder == _REDACTED

    def test_empty_placeholder_raises(self):
        with pytest.raises(ValueError, match="placeholder"):
            RedactorConfig(placeholder="")

    def test_invalid_extra_pattern_raises(self):
        with pytest.raises(ValueError, match="Invalid redactor pattern"):
            RedactorConfig(extra_patterns=["["])

    def test_from_env_defaults(self, monkeypatch):
        for key in ("CRONWRAP_REDACT_ENABLED", "CRONWRAP_REDACT_PLACEHOLDER", "CRONWRAP_REDACT_PATTERNS"):
            monkeypatch.delenv(key, raising=False)
        cfg = RedactorConfig.from_env()
        assert cfg.enabled is True
        assert cfg.placeholder == _REDACTED
        assert cfg.extra_patterns == []

    def test_from_env_disabled(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_REDACT_ENABLED", "false")
        cfg = RedactorConfig.from_env()
        assert cfg.enabled is False

    def test_from_env_custom_placeholder(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_REDACT_PLACEHOLDER", "***")
        cfg = RedactorConfig.from_env()
        assert cfg.placeholder == "***"

    def test_from_env_extra_patterns(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_REDACT_PATTERNS", r"\d{4}-\d{4},foo")
        cfg = RedactorConfig.from_env()
        assert len(cfg.extra_patterns) == 2


# ---------------------------------------------------------------------------
# redact()
# ---------------------------------------------------------------------------

class TestRedact:
    def test_redacts_password_equals(self):
        result = redact("password=hunter2")
        assert "hunter2" not in result
        assert _REDACTED in result

    def test_redacts_token_colon(self):
        result = redact("token: abc123")
        assert "abc123" not in result

    def test_redacts_api_key(self):
        result = redact("api_key=supersecret")
        assert "supersecret" not in result

    def test_plain_text_unchanged(self):
        text = "everything is fine"
        assert redact(text) == text

    def test_disabled_config_returns_original(self):
        cfg = RedactorConfig(enabled=False)
        sensitive = "password=topsecret"
        assert redact(sensitive, cfg) == sensitive

    def test_extra_pattern_applied(self):
        cfg = RedactorConfig(extra_patterns=[r"\b\d{16}\b"])
        result = redact("card: 1234567890123456", cfg)
        assert "1234567890123456" not in result
        assert _REDACTED in result

    def test_custom_placeholder(self):
        cfg = RedactorConfig(placeholder="***")
        result = redact("secret=abc", cfg)
        assert "***" in result

    def test_none_config_uses_defaults(self):
        result = redact("token=xyz", None)
        assert "xyz" not in result
