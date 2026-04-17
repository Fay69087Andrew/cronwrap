"""Tests for cronwrap.annotations."""
import pytest
from cronwrap.annotations import AnnotationConfig, Annotations


class TestAnnotationConfig:
    def test_defaults(self):
        cfg = AnnotationConfig()
        assert cfg.enabled is True
        assert cfg.max_entries == 32

    def test_zero_max_entries_raises(self):
        with pytest.raises(ValueError, match="max_entries"):
            AnnotationConfig(max_entries=0)

    def test_negative_max_entries_raises(self):
        with pytest.raises(ValueError):
            AnnotationConfig(max_entries=-1)

    def test_from_env_defaults(self, monkeypatch):
        monkeypatch.delenv("CRONWRAP_ANNOTATIONS_ENABLED", raising=False)
        monkeypatch.delenv("CRONWRAP_ANNOTATIONS_MAX_ENTRIES", raising=False)
        cfg = AnnotationConfig.from_env()
        assert cfg.enabled is True
        assert cfg.max_entries == 32

    def test_from_env_disabled(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_ANNOTATIONS_ENABLED", "false")
        cfg = AnnotationConfig.from_env()
        assert cfg.enabled is False

    def test_from_env_custom_max(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_ANNOTATIONS_MAX_ENTRIES", "10")
        cfg = AnnotationConfig.from_env()
        assert cfg.max_entries == 10


class TestAnnotations:
    def test_set_and_get(self):
        a = Annotations()
        a.set("env", "prod")
        assert a.get("env") == "prod"

    def test_value_coerced_to_str(self):
        a = Annotations()
        a.set("count", 42)
        assert a.get("count") == "42"

    def test_empty_key_raises(self):
        a = Annotations()
        with pytest.raises(ValueError, match="empty"):
            a.set("", "v")

    def test_key_too_long_raises(self):
        a = Annotations()
        with pytest.raises(ValueError, match="too long"):
            a.set("k" * 65, "v")

    def test_value_too_long_raises(self):
        a = Annotations()
        with pytest.raises(ValueError, match="too long"):
            a.set("k", "v" * 257)

    def test_limit_enforced(self):
        a = Annotations(config=AnnotationConfig(max_entries=2))
        a.set("a", "1")
        a.set("b", "2")
        with pytest.raises(ValueError, match="limit"):
            a.set("c", "3")

    def test_update_existing_key_within_limit(self):
        a = Annotations(config=AnnotationConfig(max_entries=1))
        a.set("x", "1")
        a.set("x", "2")  # update, not new entry
        assert a.get("x") == "2"

    def test_disabled_set_is_noop(self):
        a = Annotations(config=AnnotationConfig(enabled=False))
        a.set("k", "v")
        assert len(a) == 0

    def test_to_dict(self):
        a = Annotations()
        a.set("x", "1")
        a.set("y", "2")
        assert a.to_dict() == {"x": "1", "y": "2"}

    def test_merge(self):
        a = Annotations()
        a.set("x", "1")
        b = a.merge({"y": "2", "x": "overridden"})
        assert b.get("x") == "overridden"
        assert b.get("y") == "2"
        assert a.get("x") == "1"  # original unchanged

    def test_len(self):
        a = Annotations()
        assert len(a) == 0
        a.set("k", "v")
        assert len(a) == 1
