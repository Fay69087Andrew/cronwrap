"""Tests for cronwrap.suppress."""
import pytest

from cronwrap.suppress import SuppressConfig, is_suppressed, suppress_summary


class TestSuppressConfig:
    def test_defaults(self):
        cfg = SuppressConfig()
        assert cfg.codes == []
        assert cfg.enabled is True

    def test_valid_codes_stored(self):
        cfg = SuppressConfig(codes=[0, 1, 2])
        assert cfg.codes == [0, 1, 2]

    def test_negative_code_raises(self):
        with pytest.raises(ValueError, match=">= 0"):
            SuppressConfig(codes=[-1])

    def test_non_int_code_raises(self):
        with pytest.raises(TypeError):
            SuppressConfig(codes=["1"])  # type: ignore

    def test_invalid_enabled_raises(self):
        with pytest.raises(TypeError):
            SuppressConfig(enabled="yes")  # type: ignore

    def test_from_env_defaults(self, monkeypatch):
        monkeypatch.delenv("CRONWRAP_SUPPRESS_CODES", raising=False)
        monkeypatch.delenv("CRONWRAP_SUPPRESS_ENABLED", raising=False)
        cfg = SuppressConfig.from_env()
        assert cfg.codes == []
        assert cfg.enabled is True

    def test_from_env_codes(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_SUPPRESS_CODES", "1, 2, 3")
        cfg = SuppressConfig.from_env()
        assert cfg.codes == [1, 2, 3]

    def test_from_env_disabled(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_SUPPRESS_ENABLED", "false")
        cfg = SuppressConfig.from_env()
        assert cfg.enabled is False

    def test_from_env_invalid_code_raises(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_SUPPRESS_CODES", "1,abc")
        with pytest.raises(ValueError, match="Invalid exit code"):
            SuppressConfig.from_env()


class TestIsSuppressed:
    def test_suppressed_when_code_in_list(self):
        cfg = SuppressConfig(codes=[1, 2])
        assert is_suppressed(cfg, 1) is True

    def test_not_suppressed_when_code_absent(self):
        cfg = SuppressConfig(codes=[1, 2])
        assert is_suppressed(cfg, 3) is False

    def test_not_suppressed_when_disabled(self):
        cfg = SuppressConfig(codes=[1, 2], enabled=False)
        assert is_suppressed(cfg, 1) is False

    def test_zero_can_be_suppressed(self):
        cfg = SuppressConfig(codes=[0])
        assert is_suppressed(cfg, 0) is True


class TestSuppressSummary:
    def test_disabled_message(self):
        cfg = SuppressConfig(enabled=False)
        assert suppress_summary(cfg) == "suppress: disabled"

    def test_no_codes_message(self):
        cfg = SuppressConfig(codes=[])
        assert suppress_summary(cfg) == "suppress: disabled"

    def test_codes_listed_sorted(self):
        cfg = SuppressConfig(codes=[3, 1, 2])
        assert suppress_summary(cfg) == "suppress: codes=[1, 2, 3]"
