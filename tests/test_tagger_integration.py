"""Tests for cronwrap.tagger_integration."""
from __future__ import annotations

import pytest

from cronwrap.tags import TagSet
from cronwrap.runner import RunResult
from cronwrap.tagger_integration import (
    build_tags_from_env,
    enrich_tags_from_result,
    tags_summary,
    filter_tags,
)


def _result(exit_code: int = 0) -> RunResult:
    return RunResult(command="echo hi", exit_code=exit_code, stdout=b"", stderr=b"", duration=0.1)


class TestBuildTagsFromEnv:
    def test_picks_up_prefixed_vars(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_TAG_ENV", "production")
        monkeypatch.setenv("CRONWRAP_TAG_REGION", "us-east-1")
        tags = build_tags_from_env()
        assert tags.get("env") == "production"
        assert tags.get("region") == "us-east-1"

    def test_ignores_unrelated_vars(self, monkeypatch):
        monkeypatch.setenv("OTHER_VAR", "should-be-ignored")
        tags = build_tags_from_env()
        assert tags.get("other_var") is None

    def test_key_lowercased(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_TAG_MYKEY", "val")
        tags = build_tags_from_env()
        assert tags.get("mykey") == "val"

    def test_empty_env_returns_empty_tagset(self, monkeypatch):
        for k in list(__import__("os").environ):
            if k.startswith("CRONWRAP_TAG_"):
                monkeypatch.delenv(k, raising=False)
        tags = build_tags_from_env()
        assert tags.to_dict() == {}


class TestEnrichTagsFromResult:
    def test_adds_exit_code_and_status_on_success(self):
        base = TagSet(tags={"env": "prod"})
        enriched = enrich_tags_from_result(base, _result(0))
        assert enriched.get("exit_code") == "0"
        assert enriched.get("status") == "success"
        assert enriched.get("env") == "prod"

    def test_adds_failure_status_on_nonzero(self):
        base = TagSet()
        enriched = enrich_tags_from_result(base, _result(1))
        assert enriched.get("status") == "failure"
        assert enriched.get("exit_code") == "1"

    def test_does_not_mutate_base(self):
        base = TagSet(tags={"k": "v"})
        enrich_tags_from_result(base, _result(0))
        assert base.get("exit_code") is None


class TestTagsSummary:
    def test_empty_tags(self):
        assert tags_summary(TagSet()) == "tags: (none)"

    def test_sorted_output(self):
        t = TagSet(tags={"z": "last", "a": "first"})
        summary = tags_summary(t)
        assert summary.startswith("tags: a=first")
        assert "z=last" in summary


class TestFilterTags:
    def test_keeps_only_requested_keys(self):
        t = TagSet(tags={"env": "prod", "region": "eu", "team": "ops"})
        filtered = filter_tags(t, ["env", "team"])
        assert filtered.get("env") == "prod"
        assert filtered.get("team") == "ops"
        assert filtered.get("region") is None

    def test_empty_keys_returns_empty(self):
        t = TagSet(tags={"env": "prod"})
        filtered = filter_tags(t, [])
        assert filtered.to_dict() == {}
