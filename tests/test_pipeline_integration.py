"""Tests for cronwrap.pipeline_integration."""
from unittest.mock import patch, MagicMock
import pytest

from cronwrap.pipeline import PipelineConfig, PipelineResult
from cronwrap.pipeline_integration import run_pipeline, pipeline_summary, build_pipeline_config


def _run(exit_code: int, stdout: str = "", stderr: str = ""):
    r = MagicMock()
    r.exit_code = exit_code
    r.stdout = stdout
    r.stderr = stderr
    return r


class TestRunPipeline:
    def test_all_steps_run_on_success(self):
        cfg = PipelineConfig(steps=["cmd1", "cmd2"], stop_on_failure=True)
        with patch("cronwrap.pipeline_integration.run_command", side_effect=[_run(0), _run(0)]) as m:
            result = run_pipeline(cfg)
        assert result.succeeded
        assert m.call_count == 2

    def test_stops_on_failure_when_configured(self):
        cfg = PipelineConfig(steps=["cmd1", "cmd2", "cmd3"], stop_on_failure=True)
        with patch("cronwrap.pipeline_integration.run_command", side_effect=[_run(0), _run(1), _run(0)]) as m:
            result = run_pipeline(cfg)
        assert not result.succeeded
        assert m.call_count == 2
        assert result.aborted_at == 1

    def test_continues_on_failure_when_not_configured(self):
        cfg = PipelineConfig(steps=["cmd1", "cmd2", "cmd3"], stop_on_failure=False)
        with patch("cronwrap.pipeline_integration.run_command", side_effect=[_run(0), _run(1), _run(0)]) as m:
            result = run_pipeline(cfg)
        assert m.call_count == 3
        assert result.aborted_at is None

    def test_empty_steps_returns_empty_result(self):
        cfg = PipelineConfig(steps=[])
        with patch("cronwrap.pipeline_integration.run_command") as m:
            result = run_pipeline(cfg)
        assert m.call_count == 0
        assert result.succeeded

    def test_step_results_populated(self):
        cfg = PipelineConfig(steps=["echo hi"])
        with patch("cronwrap.pipeline_integration.run_command", return_value=_run(0, stdout="hi")):
            result = run_pipeline(cfg)
        assert result.step_results[0].stdout == "hi"
        assert result.step_results[0].command == "echo hi"


class TestPipelineSummary:
    def test_includes_label(self):
        r = PipelineResult(label="myjob")
        assert "myjob" in pipeline_summary(r)

    def test_includes_step_info(self):
        from cronwrap.pipeline import StepResult
        sr = StepResult(index=0, command="echo hi", exit_code=0, stdout="", stderr="")
        r = PipelineResult(label="x", step_results=[sr])
        summary = pipeline_summary(r)
        assert "echo hi" in summary
        assert "✓" in summary

    def test_failed_step_shows_exit_code(self):
        from cronwrap.pipeline import StepResult
        sr = StepResult(index=0, command="bad", exit_code=2, stdout="", stderr="oops")
        r = PipelineResult(label="x", step_results=[sr], aborted_at=0)
        summary = pipeline_summary(r)
        assert "exit_code=2" in summary
        assert "aborted" in summary


def test_build_pipeline_config_returns_config(monkeypatch):
    monkeypatch.delenv("CRONWRAP_PIPELINE_STEPS", raising=False)
    cfg = build_pipeline_config()
    assert isinstance(cfg, PipelineConfig)
