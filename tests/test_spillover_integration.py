"""Tests for cronwrap.spillover_integration."""
import logging
import sys

import pytest

from cronwrap.spillover import SpilloverConfig
from cronwrap.spillover_integration import (
    build_spillover_config,
    evaluate_spillover,
    report_spillover,
)


def _cfg(**kwargs) -> SpilloverConfig:
    return SpilloverConfig(**kwargs)


class TestBuildSpilloverConfig:
    def test_returns_spillover_config(self, monkeypatch):
        monkeypatch.delenv("CRONWRAP_SPILLOVER_INTERVAL", raising=False)
        cfg = build_spillover_config()
        assert isinstance(cfg, SpilloverConfig)


class TestEvaluateSpillover:
    def test_no_spill_returns_result(self):
        cfg = _cfg(interval_seconds=3600.0)
        result = evaluate_spillover(60.0, cfg)
        assert result.spilled is False

    def test_spill_logs_warning(self, caplog):
        cfg = _cfg(interval_seconds=60.0, warn_only=True)
        with caplog.at_level(logging.WARNING, logger="cronwrap.spillover_integration"):
            result = evaluate_spillover(120.0, cfg)
        assert result.spilled is True
        assert any("SPILLOVER" in r.message for r in caplog.records)

    def test_spill_with_job_name_in_log(self, caplog):
        cfg = _cfg(interval_seconds=60.0, warn_only=True)
        with caplog.at_level(logging.WARNING, logger="cronwrap.spillover_integration"):
            evaluate_spillover(120.0, cfg, job_name="backup")
        assert any("[backup]" in r.message for r in caplog.records)

    def test_spill_exits_when_not_warn_only(self):
        cfg = _cfg(interval_seconds=60.0, warn_only=False)
        with pytest.raises(SystemExit) as exc_info:
            evaluate_spillover(120.0, cfg)
        assert exc_info.value.code == 1

    def test_no_spill_uses_debug_log(self, caplog):
        cfg = _cfg(interval_seconds=3600.0)
        with caplog.at_level(logging.DEBUG, logger="cronwrap.spillover_integration"):
            evaluate_spillover(10.0, cfg)
        assert any("OK" in r.message for r in caplog.records)

    def test_uses_default_config_when_none(self):
        result = evaluate_spillover(1.0)
        assert result.interval_seconds == 3600.0


class TestReportSpillover:
    def test_ok_report(self):
        cfg = _cfg(interval_seconds=3600.0)
        from cronwrap.spillover import check_spillover
        result = check_spillover(60.0, cfg)
        report = report_spillover(result)
        assert "spillover=OK" in report
        assert "elapsed=60.0s" in report

    def test_spilled_report(self):
        cfg = _cfg(interval_seconds=100.0)
        from cronwrap.spillover import check_spillover
        result = check_spillover(150.0, cfg)
        report = report_spillover(result)
        assert "spillover=SPILLED" in report
        assert "overflow=50.0s" in report
