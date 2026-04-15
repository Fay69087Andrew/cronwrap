"""Tests for cronwrap.runbook_integration."""
import pytest
from cronwrap.runbook import RunbookConfig
from cronwrap.runbook_integration import (
    enrich_alert_context,
    append_runbook_to_body,
    runbook_report,
)


def _cfg(url=None, title="Runbook", enabled=True):
    return RunbookConfig(url=url, title=title, enabled=enabled)


class TestEnrichAlertContext:
    def test_adds_none_when_no_url(self):
        result = enrich_alert_context({"job": "backup"}, _cfg())
        assert result["runbook"] is None
        assert result["job"] == "backup"

    def test_adds_link_when_configured(self):
        cfg = _cfg(url="https://wiki.example.com", title="Wiki")
        result = enrich_alert_context({"job": "backup"}, cfg)
        assert result["runbook"] == "[Wiki](https://wiki.example.com)"

    def test_does_not_mutate_original(self):
        original = {"job": "backup"}
        enrich_alert_context(original, _cfg(url="https://example.com"))
        assert "runbook" not in original

    def test_adds_none_when_disabled(self):
        cfg = _cfg(url="https://example.com", enabled=False)
        result = enrich_alert_context({}, cfg)
        assert result["runbook"] is None


class TestAppendRunbookToBody:
    def test_unchanged_when_no_url(self):
        body = "Job failed."
        assert append_runbook_to_body(body, _cfg()) == body

    def test_unchanged_when_disabled(self):
        cfg = _cfg(url="https://example.com", enabled=False)
        body = "Job failed."
        assert append_runbook_to_body(body, cfg) == body

    def test_appends_link(self):
        cfg = _cfg(url="https://example.com/rb", title="Ops")
        result = append_runbook_to_body("Job failed.", cfg)
        assert "Runbook: [Ops](https://example.com/rb)" in result
        assert result.startswith("Job failed.")

    def test_separator_present(self):
        cfg = _cfg(url="https://example.com/rb")
        result = append_runbook_to_body("Body text.", cfg)
        assert "---" in result


class TestRunbookReport:
    def test_contains_section_header(self):
        report = runbook_report(_cfg())
        assert "Runbook Configuration" in report

    def test_contains_enabled_field(self):
        report = runbook_report(_cfg(enabled=False))
        assert "enabled" in report
        assert "False" in report

    def test_contains_url_field(self):
        cfg = _cfg(url="https://example.com")
        report = runbook_report(cfg)
        assert "https://example.com" in report

    def test_contains_summary(self):
        cfg = _cfg(url="https://example.com", title="Guide")
        report = runbook_report(cfg)
        assert "summary" in report
        assert "Guide" in report
