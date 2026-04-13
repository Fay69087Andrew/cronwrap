"""Tests for cronwrap.tags."""

from __future__ import annotations

import pytest

from cronwrap.tags import TagSet, from_env, parse_tags


# ---------------------------------------------------------------------------
# TagSet
# ---------------------------------------------------------------------------

class TestTagSet:
    def test_empty_by_default(self):
        ts = TagSet()
        assert ts.to_dict() == {}

    def test_values_coerced_to_str(self):
        ts = TagSet(tags={"retries": 3})  # type: ignore[arg-type]
        assert ts.get("retries") == "3"

    def test_invalid_key_raises(self):
        with pytest.raises(ValueError, match="Invalid tag key"):
            TagSet(tags={"bad key!": "value"})

    def test_key_too_long_raises(self):
        with pytest.raises(ValueError, match="Invalid tag key"):
            TagSet(tags={"a" * 65: "value"})

    def test_value_too_long_raises(self):
        with pytest.raises(ValueError, match="exceeds 256"):
            TagSet(tags={"key": "x" * 257})

    def test_get_existing_key(self):
        ts = TagSet(tags={"env": "prod"})
        assert ts.get("env") == "prod"

    def test_get_missing_key_returns_default(self):
        ts = TagSet(tags={"env": "prod"})
        assert ts.get("team", "unknown") == "unknown"

    def test_to_dict_returns_copy(self):
        ts = TagSet(tags={"a": "1"})
        d = ts.to_dict()
        d["b"] = "2"
        assert "b" not in ts.tags

    def test_merge_combines_tags(self):
        ts1 = TagSet(tags={"env": "dev", "region": "us"})
        ts2 = TagSet(tags={"env": "prod", "team": "ops"})
        merged = ts1.merge(ts2)
        assert merged.get("env") == "prod"      # overridden
        assert merged.get("region") == "us"     # preserved
        assert merged.get("team") == "ops"      # new

    def test_merge_does_not_mutate_originals(self):
        ts1 = TagSet(tags={"env": "dev"})
        ts2 = TagSet(tags={"env": "prod"})
        ts1.merge(ts2)
        assert ts1.get("env") == "dev"


# ---------------------------------------------------------------------------
# from_env
# ---------------------------------------------------------------------------

class TestFromEnv:
    def test_reads_prefixed_vars(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_TAG_ENV", "staging")
        monkeypatch.setenv("CRONWRAP_TAG_TEAM", "platform")
        monkeypatch.delenv("CRONWRAP_TAG_", raising=False)
        ts = from_env()
        assert ts.get("env") == "staging"
        assert ts.get("team") == "platform"

    def test_ignores_unrelated_vars(self, monkeypatch):
        monkeypatch.setenv("SOME_OTHER_VAR", "value")
        ts = from_env()
        assert "some_other_var" not in ts.tags

    def test_empty_suffix_skipped(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_TAG_", "oops")
        ts = from_env()
        assert "" not in ts.tags

    def test_custom_prefix(self, monkeypatch):
        monkeypatch.setenv("JOB_TAG_SERVICE", "worker")
        ts = from_env(prefix="JOB_TAG_")
        assert ts.get("service") == "worker"


# ---------------------------------------------------------------------------
# parse_tags
# ---------------------------------------------------------------------------

class TestParseTags:
    def test_single_pair(self):
        ts = parse_tags("env=prod")
        assert ts.get("env") == "prod"

    def test_multiple_pairs(self):
        ts = parse_tags("env=prod,team=ops,region=eu")
        assert ts.get("team") == "ops"
        assert ts.get("region") == "eu"

    def test_empty_string_returns_empty(self):
        ts = parse_tags("")
        assert ts.to_dict() == {}

    def test_missing_equals_raises(self):
        with pytest.raises(ValueError, match="missing '='"):
            parse_tags("envprod")

    def test_whitespace_stripped(self):
        ts = parse_tags(" env = prod , team = ops ")
        assert ts.get("env") == "prod"
        assert ts.get("team") == "ops"
