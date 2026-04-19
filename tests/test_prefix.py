"""Tests for cronwrap.prefix."""
import pytest
from cronwrap.prefix import PrefixConfig, build_prefix, prefix_lines, prefix_summary


class TestPrefixConfig:
    def test_defaults(self):
        cfg = PrefixConfig()
        assert cfg.enabled is True
        assert cfg.template == "[{job}]"
        assert cfg.include_timestamp is False
        assert cfg.job_name == "cronwrap"

    def test_empty_template_raises(self):
        with pytest.raises(ValueError, match="template"):
            PrefixConfig(template="   ")

    def test_empty_job_name_raises(self):
        with pytest.raises(ValueError, match="job_name"):
            PrefixConfig(job_name="")

    def test_invalid_enabled_raises(self):
        with pytest.raises(TypeError, match="enabled"):
            PrefixConfig(enabled="yes")  # type: ignore

    def test_template_stripped(self):
        cfg = PrefixConfig(template="  [{job}]  ")
        assert cfg.template == "[{job}]"

    def test_from_env_defaults(self, monkeypatch):
        for k in ("CRONWRAP_PREFIX_ENABLED", "CRONWRAP_PREFIX_TEMPLATE",
                  "CRONWRAP_PREFIX_TIMESTAMP", "CRONWRAP_JOB_NAME"):
            monkeypatch.delenv(k, raising=False)
        cfg = PrefixConfig.from_env()
        assert cfg.enabled is True
        assert cfg.job_name == "cronwrap"

    def test_from_env_custom(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_PREFIX_ENABLED", "false")
        monkeypatch.setenv("CRONWRAP_JOB_NAME", "myjob")
        cfg = PrefixConfig.from_env()
        assert cfg.enabled is False
        assert cfg.job_name == "myjob"


class TestBuildPrefix:
    def test_basic_prefix(self):
        cfg = PrefixConfig(job_name="backup")
        pfx = build_prefix(cfg)
        assert pfx == "[backup] "

    def test_disabled_returns_empty(self):
        cfg = PrefixConfig(enabled=False)
        assert build_prefix(cfg) == ""

    def test_includes_timestamp_when_enabled(self):
        cfg = PrefixConfig(job_name="j", include_timestamp=True)
        pfx = build_prefix(cfg)
        assert "[j]" in pfx
        assert len(pfx) > len("[j] ")


class TestPrefixLines:
    def test_prefixes_each_line(self):
        cfg = PrefixConfig(job_name="x")
        result = prefix_lines("hello\nworld", cfg)
        assert result == "[x] hello\n[x] world"

    def test_empty_lines_not_prefixed(self):
        cfg = PrefixConfig(job_name="x")
        result = prefix_lines("a\n\nb", cfg)
        lines = result.splitlines()
        assert lines[1] == ""

    def test_disabled_returns_original(self):
        cfg = PrefixConfig(enabled=False)
        text = "line1\nline2"
        assert prefix_lines(text, cfg) == text

    def test_empty_text_returns_empty(self):
        cfg = PrefixConfig()
        assert prefix_lines("", cfg) == ""


def test_prefix_summary_keys():
    cfg = PrefixConfig(job_name="test")
    s = prefix_summary(cfg)
    assert set(s.keys()) == {"enabled", "template", "include_timestamp", "job_name"}
    assert s["job_name"] == "test"
