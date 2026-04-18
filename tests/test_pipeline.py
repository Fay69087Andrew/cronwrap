"""Tests for cronwrap.pipeline."""
import pytest
from cronwrap.pipeline import PipelineConfig, PipelineResult, StepResult


class TestPipelineConfig:
    def test_defaults(self):
        cfg = PipelineConfig()
        assert cfg.steps == []
        assert cfg.stop_on_failure is True
        assert cfg.label == "pipeline"

    def test_empty_steps_filtered(self):
        cfg = PipelineConfig(steps=["", "  ", "echo hi"])
        assert cfg.steps == ["echo hi"]

    def test_label_stripped(self):
        cfg = PipelineConfig(label="  myjob  ")
        assert cfg.label == "myjob"

    def test_empty_label_raises(self):
        with pytest.raises(ValueError):
            PipelineConfig(label="   ")

    def test_invalid_stop_on_failure_raises(self):
        with pytest.raises(TypeError):
            PipelineConfig(stop_on_failure="yes")  # type: ignore

    def test_from_env_defaults(self, monkeypatch):
        monkeypatch.delenv("CRONWRAP_PIPELINE_STEPS", raising=False)
        monkeypatch.delenv("CRONWRAP_PIPELINE_STOP_ON_FAILURE", raising=False)
        monkeypatch.delenv("CRONWRAP_PIPELINE_LABEL", raising=False)
        cfg = PipelineConfig.from_env()
        assert cfg.steps == []
        assert cfg.stop_on_failure is True
        assert cfg.label == "pipeline"

    def test_from_env_parses_steps(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_PIPELINE_STEPS", "echo a;echo b; echo c")
        cfg = PipelineConfig.from_env()
        assert cfg.steps == ["echo a", "echo b", "echo c"]

    def test_from_env_stop_on_failure_false(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_PIPELINE_STOP_ON_FAILURE", "false")
        cfg = PipelineConfig.from_env()
        assert cfg.stop_on_failure is False


def _step(idx: int, exit_code: int) -> StepResult:
    return StepResult(index=idx, command=f"cmd{idx}", exit_code=exit_code, stdout="", stderr="")


class TestStepResult:
    def test_succeeded_on_zero(self):
        assert _step(0, 0).succeeded is True

    def test_not_succeeded_on_nonzero(self):
        assert _step(0, 1).succeeded is False


class TestPipelineResult:
    def test_succeeded_all_pass(self):
        r = PipelineResult(label="x", step_results=[_step(0, 0), _step(1, 0)])
        assert r.succeeded is True

    def test_not_succeeded_on_failure(self):
        r = PipelineResult(label="x", step_results=[_step(0, 0), _step(1, 1)])
        assert r.succeeded is False

    def test_counts(self):
        r = PipelineResult(label="x", step_results=[_step(0, 0), _step(1, 1)])
        assert r.total_steps == 2
        assert r.passed_steps == 1

    def test_str_ok(self):
        r = PipelineResult(label="myjob", step_results=[_step(0, 0)])
        assert "OK" in str(r)
        assert "myjob" in str(r)

    def test_str_failed(self):
        r = PipelineResult(label="myjob", step_results=[_step(0, 1)])
        assert "FAILED" in str(r)
