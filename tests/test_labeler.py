"""Tests for cronwrap.labeler."""
import pytest

from cronwrap.labeler import LabelSet, from_env, label_summary


class TestLabelSet:
    def test_empty_by_default(self):
        ls = LabelSet()
        assert ls.to_dict() == {}
        assert len(ls) == 0

    def test_valid_labels_stored(self):
        ls = LabelSet(labels={"env": "prod", "team": "platform"})
        assert ls.get("env") == "prod"
        assert ls.get("team") == "platform"

    def test_values_coerced_to_str(self):
        ls = LabelSet(labels={"retries": 3})
        assert ls.get("retries") == "3"

    def test_invalid_key_raises(self):
        with pytest.raises(ValueError, match="Invalid label key"):
            LabelSet(labels={"Bad-Key!": "value"})

    def test_key_starting_with_digit_raises(self):
        with pytest.raises(ValueError, match="Invalid label key"):
            LabelSet(labels={"1abc": "value"})

    def test_key_too_long_raises(self):
        long_key = "a" * 64
        with pytest.raises(ValueError, match="Invalid label key"):
            LabelSet(labels={long_key: "value"})

    def test_value_too_long_raises(self):
        with pytest.raises(ValueError, match="exceeds"):
            LabelSet(labels={"env": "x" * 257})

    def test_value_at_max_length_ok(self):
        ls = LabelSet(labels={"env": "x" * 256})
        assert len(ls.get("env")) == 256

    def test_get_missing_key_returns_none(self):
        ls = LabelSet()
        assert ls.get("missing") is None

    def test_to_dict_returns_copy(self):
        ls = LabelSet(labels={"env": "prod"})
        d = ls.to_dict()
        d["env"] = "staging"
        assert ls.get("env") == "prod"

    def test_merge_combines_labels(self):
        a = LabelSet(labels={"env": "prod", "region": "us"})
        b = LabelSet(labels={"env": "staging", "team": "ops"})
        merged = a.merge(b)
        assert merged.get("env") == "staging"
        assert merged.get("region") == "us"
        assert merged.get("team") == "ops"

    def test_merge_does_not_mutate_originals(self):
        a = LabelSet(labels={"env": "prod"})
        b = LabelSet(labels={"env": "staging"})
        a.merge(b)
        assert a.get("env") == "prod"

    def test_key_with_dots_and_dashes_ok(self):
        ls = LabelSet(labels={"app.name": "cronwrap", "k8s.io": "true"})
        assert ls.get("app.name") == "cronwrap"


class TestFromEnv:
    def test_empty_when_no_matching_vars(self, monkeypatch):
        monkeypatch.delenv("CRONWRAP_LABEL_ENV", raising=False)
        ls = from_env()
        assert ls.get("env") is None

    def test_picks_up_matching_vars(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_LABEL_ENV", "production")
        monkeypatch.setenv("CRONWRAP_LABEL_TEAM", "platform")
        ls = from_env()
        assert ls.get("env") == "production"
        assert ls.get("team") == "platform"

    def test_ignores_non_matching_vars(self, monkeypatch):
        monkeypatch.setenv("OTHER_VAR", "ignored")
        ls = from_env()
        assert ls.get("other_var") is None

    def test_key_lowercased(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_LABEL_REGION", "eu-west")
        ls = from_env()
        assert ls.get("region") == "eu-west"

    def test_custom_prefix(self, monkeypatch):
        monkeypatch.setenv("JOB_LABEL_ENV", "dev")
        ls = from_env(prefix="JOB_LABEL_")
        assert ls.get("env") == "dev"


class TestLabelSummary:
    def test_empty_label_set(self):
        ls = LabelSet()
        assert label_summary(ls) == "labels: (none)"

    def test_single_label(self):
        ls = LabelSet(labels={"env": "prod"})
        assert label_summary(ls) == "labels: env=prod"

    def test_multiple_labels_sorted(self):
        ls = LabelSet(labels={"team": "ops", "env": "prod"})
        result = label_summary(ls)
        assert result == "labels: env=prod, team=ops"
