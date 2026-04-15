"""Tests for cronwrap.sanitizer."""
import pytest

from cronwrap.sanitizer import SanitizerConfig, sanitize


class TestSanitizerConfig:
    def test_defaults(self):
        cfg = SanitizerConfig()
        assert cfg.strip_ansi is True
        assert cfg.strip_non_printable is True
        assert cfg.max_length == 0
        assert cfg.replacement == ""

    def test_negative_max_length_raises(self):
        with pytest.raises(ValueError, match="max_length"):
            SanitizerConfig(max_length=-1)

    def test_non_str_replacement_raises(self):
        with pytest.raises(TypeError, match="replacement"):
            SanitizerConfig(replacement=42)  # type: ignore[arg-type]

    def test_from_env_defaults(self):
        cfg = SanitizerConfig.from_env({})
        assert cfg.strip_ansi is True
        assert cfg.strip_non_printable is True
        assert cfg.max_length == 0
        assert cfg.replacement == ""

    def test_from_env_disabled(self):
        cfg = SanitizerConfig.from_env(
            {
                "CRONWRAP_SANITIZE_ANSI": "false",
                "CRONWRAP_SANITIZE_NON_PRINTABLE": "0",
            }
        )
        assert cfg.strip_ansi is False
        assert cfg.strip_non_printable is False

    def test_from_env_max_length_and_replacement(self):
        cfg = SanitizerConfig.from_env(
            {
                "CRONWRAP_SANITIZE_MAX_LENGTH": "200",
                "CRONWRAP_SANITIZE_REPLACEMENT": "?",
            }
        )
        assert cfg.max_length == 200
        assert cfg.replacement == "?"

    def test_from_env_invalid_max_length_raises(self):
        """Non-integer value for CRONWRAP_SANITIZE_MAX_LENGTH should raise ValueError."""
        with pytest.raises(ValueError):
            SanitizerConfig.from_env({"CRONWRAP_SANITIZE_MAX_LENGTH": "notanumber"})


class TestSanitize:
    def test_strips_ansi_color_codes(self):
        raw = "\x1b[31mERROR\x1b[0m: something failed"
        assert sanitize(raw) == "ERROR: something failed"

    def test_strips_non_printable(self):
        raw = "hello\x00world\x07"
        assert sanitize(raw) == "helloworld"

    def test_preserves_tab_and_newline(self):
        raw = "col1\tcol2\nrow2"
        assert sanitize(raw) == raw

    def test_replacement_character_used(self):
        cfg = SanitizerConfig(replacement="*")
        raw = "\x1b[1mbold\x1b[0m"
        result = sanitize(raw, cfg)
        assert "*" in result
        assert "\x1b" not in result

    def test_max_length_truncates(self):
        cfg = SanitizerConfig(max_length=5)
        assert sanitize("hello world", cfg) == "hello"

    def test_max_length_zero_means_unlimited(self):
        cfg = SanitizerConfig(max_length=0)
        long_text = "a" * 10_000
        assert len(sanitize(long_text, cfg)) == 10_000

    def test_max_length_exact_boundary(self):
        """Output exactly at max_length should not be truncated."""
        cfg = SanitizerConfig(max_length=5)
        assert sanitize("hello", cfg) == "hello"

    def test_strip_ansi_false_preserves_codes(self):
        cfg = SanitizerConfig(strip_ansi=False, strip_non_printable=False)
        raw = "\x1b[31mred\x1b[0m"
        assert sanitize(raw, cfg) == raw

    def test_plain_text_unchanged(self):
        raw = "Everything is fine."
        assert sanitize(raw) == raw

    def test_none_config_uses_defaults(self):
        raw = "\x1b[32mok\x1b[0m"
        assert sanitize(raw, None) == "ok"
