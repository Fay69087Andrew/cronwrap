"""Tests for cronwrap.correlator."""
from __future__ import annotations

import pytest

from cronwrap.correlator import (
    CorrelatorConfig,
    correlation_summary,
    generate_correlation_id,
)


# ---------------------------------------------------------------------------
# CorrelatorConfig
# ---------------------------------------------------------------------------

class TestCorrelatorConfig:
    def test_defaults(self):
        cfg = CorrelatorConfig()
        assert cfg.enabled is True
        assert cfg.prefix == ""
        assert cfg.env_var == "CRONWRAP_CORRELATION_ID"

    def test_prefix_too_long_raises(self):
        with pytest.raises(ValueError, match="prefix"):
            CorrelatorConfig(prefix="x" * 33)

    def test_empty_env_var_raises(self):
        with pytest.raises(ValueError, match="env_var"):
            CorrelatorConfig(env_var="")

    def test_non_string_prefix_raises(self):
        with pytest.raises(TypeError):
            CorrelatorConfig(prefix=123)  # type: ignore[arg-type]

    def test_from_env_defaults(self, monkeypatch):
        for key in (
            "CRONWRAP_CORRELATION_ENABLED",
            "CRONWRAP_CORRELATION_PREFIX",
            "CRONWRAP_CORRELATION_ENV_VAR",
        ):
            monkeypatch.delenv(key, raising=False)
        cfg = CorrelatorConfig.from_env()
        assert cfg.enabled is True
        assert cfg.prefix == ""
        assert cfg.env_var == "CRONWRAP_CORRELATION_ID"

    def test_from_env_disabled(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_CORRELATION_ENABLED", "false")
        cfg = CorrelatorConfig.from_env()
        assert cfg.enabled is False

    def test_from_env_custom_prefix(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_CORRELATION_PREFIX", "job-")
        cfg = CorrelatorConfig.from_env()
        assert cfg.prefix == "job-"


# ---------------------------------------------------------------------------
# generate_correlation_id
# ---------------------------------------------------------------------------

class TestGenerateCorrelationId:
    def test_returns_nonempty_string_when_enabled(self):
        cfg = CorrelatorConfig()
        cid = generate_correlation_id(cfg)
        assert isinstance(cid, str)
        assert len(cid) > 0

    def test_returns_empty_string_when_disabled(self):
        cfg = CorrelatorConfig(enabled=False)
        assert generate_correlation_id(cfg) == ""

    def test_prefix_prepended(self):
        cfg = CorrelatorConfig(prefix="run-")
        cid = generate_correlation_id(cfg)
        assert cid.startswith("run-")

    def test_unique_ids_generated(self):
        cfg = CorrelatorConfig()
        ids = {generate_correlation_id(cfg) for _ in range(50)}
        assert len(ids) == 50

    def test_reuses_env_var_if_set(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_CORRELATION_ID", "inherited-id-abc")
        cfg = CorrelatorConfig()
        assert generate_correlation_id(cfg) == "inherited-id-abc"

    def test_env_var_not_reused_when_disabled(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_CORRELATION_ID", "inherited-id-abc")
        cfg = CorrelatorConfig(enabled=False)
        assert generate_correlation_id(cfg) == ""


# ---------------------------------------------------------------------------
# correlation_summary
# ---------------------------------------------------------------------------

class TestCorrelationSummary:
    def test_non_empty_id(self):
        assert correlation_summary("abc123") == "correlation_id=abc123"

    def test_empty_id_shows_disabled(self):
        assert correlation_summary("") == "correlation_id=<disabled>"
