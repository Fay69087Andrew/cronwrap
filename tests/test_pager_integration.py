"""Tests for cronwrap.pager_integration."""
import pytest
from unittest.mock import patch, MagicMock
from cronwrap.pager import PagerConfig
from cronwrap.pager_integration import (
    build_event_from_result,
    page_on_failure,
    pager_summary,
)
from cronwrap.runner import RunResult


def _result(exit_code: int = 0, stdout: str = "", stderr: str = "") -> RunResult:
    return RunResult(
        command="echo hi",
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        duration=1.0,
    )


class TestBuildEventFromResult:
    def test_summary_contains_command(self):
        ev = build_event_from_result(_result(1), PagerConfig())
        assert "echo hi" in ev.summary

    def test_summary_uses_job_name_when_given(self):
        ev = build_event_from_result(_result(1), PagerConfig(), job_name="my-job")
        assert "my-job" in ev.summary

    def test_details_include_exit_code(self):
        ev = build_event_from_result(_result(2), PagerConfig())
        assert ev.custom_details["exit_code"] == 2

    def test_stdout_tail_included_when_present(self):
        ev = build_event_from_result(_result(1, stdout="out"), PagerConfig())
        assert ev.custom_details["stdout_tail"] == "out"

    def test_no_stdout_key_when_empty(self):
        ev = build_event_from_result(_result(1, stdout=""), PagerConfig())
        assert "stdout_tail" not in ev.custom_details


class TestPageOnFailure:
    def test_returns_none_on_success(self):
        cfg = PagerConfig(enabled=True, routing_key="k")
        assert page_on_failure(_result(0), config=cfg) is None

    def test_returns_none_when_disabled(self):
        cfg = PagerConfig(enabled=False)
        assert page_on_failure(_result(1), config=cfg) is None

    def test_calls_send_page_on_failure(self):
        cfg = PagerConfig(enabled=True, routing_key="k")
        with patch("cronwrap.pager_integration.send_page", return_value="dk-1") as mock_send:
            result = page_on_failure(_result(1), config=cfg)
        mock_send.assert_called_once()
        assert result == "dk-1"


class TestPagerSummary:
    def test_disabled_message(self):
        cfg = PagerConfig(enabled=False)
        assert "disabled" in pager_summary(None, cfg)

    def test_sent_message_with_key(self):
        cfg = PagerConfig(enabled=True, routing_key="k")
        msg = pager_summary("dk-abc", cfg)
        assert "dk-abc" in msg

    def test_no_alert_message(self):
        cfg = PagerConfig(enabled=True, routing_key="k")
        msg = pager_summary(None, cfg)
        assert "no alert" in msg
