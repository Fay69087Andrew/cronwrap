"""Tests for cronwrap.env_validator."""
import os
import pytest

from cronwrap.env_validator import (
    EnvValidatorConfig,
    ValidationResult,
    validate_env,
)


# ---------------------------------------------------------------------------
# EnvValidatorConfig
# ---------------------------------------------------------------------------

class TestEnvValidatorConfig:
    def test_defaults(self):
        cfg = EnvValidatorConfig()
        assert cfg.required == []

    def test_names_stripped(self):
        cfg = EnvValidatorConfig(required=["  FOO  ", "BAR"])
        assert cfg.required == ["FOO", "BAR"]

    def test_empty_string_name_raises(self):
        with pytest.raises(ValueError):
            EnvValidatorConfig(required=[""])

    def test_whitespace_only_name_raises(self):
        with pytest.raises(ValueError):
            EnvValidatorConfig(required=["   "])

    def test_from_env_empty(self, monkeypatch):
        monkeypatch.delenv("CRONWRAP_REQUIRE_ENV", raising=False)
        cfg = EnvValidatorConfig.from_env()
        assert cfg.required == []

    def test_from_env_parses_csv(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_REQUIRE_ENV", "FOO, BAR , BAZ")
        cfg = EnvValidatorConfig.from_env()
        assert cfg.required == ["FOO", "BAR", "BAZ"]

    def test_from_env_single_value(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_REQUIRE_ENV", "SECRET_KEY")
        cfg = EnvValidatorConfig.from_env()
        assert cfg.required == ["SECRET_KEY"]


# ---------------------------------------------------------------------------
# ValidationResult
# ---------------------------------------------------------------------------

class TestValidationResult:
    def test_ok_when_no_missing(self):
        r = ValidationResult(missing=[])
        assert r.ok is True

    def test_not_ok_when_missing(self):
        r = ValidationResult(missing=["FOO"])
        assert r.ok is False

    def test_str_ok(self):
        assert "OK" in str(ValidationResult())

    def test_str_missing(self):
        r = ValidationResult(missing=["FOO", "BAR"])
        s = str(r)
        assert "MISSING" in s
        assert "FOO" in s
        assert "BAR" in s


# ---------------------------------------------------------------------------
# validate_env
# ---------------------------------------------------------------------------

class TestValidateEnv:
    def test_all_present_returns_ok(self, monkeypatch):
        monkeypatch.setenv("MY_VAR", "hello")
        cfg = EnvValidatorConfig(required=["MY_VAR"])
        result = validate_env(cfg)
        assert result.ok
        assert result.missing == []

    def test_missing_var_captured(self, monkeypatch):
        monkeypatch.delenv("GHOST_VAR", raising=False)
        cfg = EnvValidatorConfig(required=["GHOST_VAR"])
        result = validate_env(cfg)
        assert not result.ok
        assert "GHOST_VAR" in result.missing

    def test_empty_value_treated_as_missing(self, monkeypatch):
        monkeypatch.setenv("EMPTY_VAR", "")
        cfg = EnvValidatorConfig(required=["EMPTY_VAR"])
        result = validate_env(cfg)
        assert not result.ok

    def test_whitespace_value_treated_as_missing(self, monkeypatch):
        monkeypatch.setenv("BLANK_VAR", "   ")
        cfg = EnvValidatorConfig(required=["BLANK_VAR"])
        result = validate_env(cfg)
        assert not result.ok

    def test_empty_required_list_always_ok(self):
        cfg = EnvValidatorConfig(required=[])
        result = validate_env(cfg)
        assert result.ok

    def test_partial_missing_lists_only_missing(self, monkeypatch):
        monkeypatch.setenv("PRESENT", "yes")
        monkeypatch.delenv("ABSENT", raising=False)
        cfg = EnvValidatorConfig(required=["PRESENT", "ABSENT"])
        result = validate_env(cfg)
        assert not result.ok
        assert result.missing == ["ABSENT"]
