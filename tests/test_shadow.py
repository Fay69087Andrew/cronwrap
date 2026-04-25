"""Tests for cronwrap.shadow and cronwrap.shadow_integration."""
from __future__ import annotations

import pytest

from cronwrap.shadow import (
    ShadowConfig,
    ShadowResult,
    compare_results,
    _hash,
)
from cronwrap.shadow_integration import shadow_report


# ---------------------------------------------------------------------------
# TestShadowConfig
# ---------------------------------------------------------------------------

class TestShadowConfig:
    def test_defaults(self):
        cfg = ShadowConfig()
        assert cfg.enabled is False
        assert cfg.reference_command == ""
        assert cfg.compare_stdout is True
        assert cfg.compare_exit_code is True
        assert cfg.algorithm == "sha256"

    def test_algorithm_lowercased(self):
        cfg = ShadowConfig(algorithm="SHA256")
        assert cfg.algorithm == "sha256"

    def test_invalid_algorithm_raises(self):
        with pytest.raises(ValueError, match="algorithm"):
            ShadowConfig(algorithm="rot13")

    def test_enabled_without_command_raises(self):
        with pytest.raises(ValueError, match="reference_command"):
            ShadowConfig(enabled=True, reference_command="")

    def test_enabled_with_command_ok(self):
        cfg = ShadowConfig(enabled=True, reference_command="echo hello")
        assert cfg.enabled is True

    def test_from_env_defaults(self):
        cfg = ShadowConfig.from_env({})
        assert cfg.enabled is False

    def test_from_env_enabled(self):
        cfg = ShadowConfig.from_env({
            "CRONWRAP_SHADOW_ENABLED": "true",
            "CRONWRAP_SHADOW_COMMAND": "echo ref",
            "CRONWRAP_SHADOW_ALGORITHM": "md5",
        })
        assert cfg.enabled is True
        assert cfg.reference_command == "echo ref"
        assert cfg.algorithm == "md5"

    def test_from_env_compare_flags(self):
        cfg = ShadowConfig.from_env({
            "CRONWRAP_SHADOW_COMPARE_STDOUT": "false",
            "CRONWRAP_SHADOW_COMPARE_EXIT_CODE": "false",
        })
        assert cfg.compare_stdout is False
        assert cfg.compare_exit_code is False


# ---------------------------------------------------------------------------
# TestCompareResults
# ---------------------------------------------------------------------------

class TestCompareResults:
    def _cfg(self, **kw) -> ShadowConfig:
        return ShadowConfig(**kw)

    def test_identical_outputs_no_divergence(self):
        cfg = self._cfg()
        r = compare_results(b"hello", b"hello", 0, 0, cfg)
        assert r.stdout_match is True
        assert r.exit_code_match is True
        assert r.diverged is False

    def test_different_stdout_diverges(self):
        cfg = self._cfg()
        r = compare_results(b"hello", b"world", 0, 0, cfg)
        assert r.stdout_match is False
        assert r.diverged is True

    def test_different_exit_codes_diverges(self):
        cfg = self._cfg()
        r = compare_results(b"x", b"x", 0, 1, cfg)
        assert r.exit_code_match is False
        assert r.diverged is True

    def test_stdout_compare_disabled_ignores_diff(self):
        cfg = self._cfg(compare_stdout=False)
        r = compare_results(b"hello", b"world", 0, 0, cfg)
        assert r.stdout_match is True
        assert r.diverged is False

    def test_exit_code_compare_disabled_ignores_diff(self):
        cfg = self._cfg(compare_exit_code=False)
        r = compare_results(b"x", b"x", 0, 99, cfg)
        assert r.exit_code_match is True
        assert r.diverged is False

    def test_none_stdout_treated_as_empty(self):
        cfg = self._cfg()
        r = compare_results(None, None, 0, 0, cfg)
        assert r.stdout_match is True


# ---------------------------------------------------------------------------
# TestShadowReport
# ---------------------------------------------------------------------------

class TestShadowReport:
    def test_none_returns_disabled(self):
        assert shadow_report(None) == "shadow: disabled"

    def test_result_returns_summary(self):
        cfg = ShadowConfig()
        r = compare_results(b"ok", b"ok", 0, 0, cfg)
        report = shadow_report(r)
        assert "shadow:" in report
        assert "diverged=False" in report
