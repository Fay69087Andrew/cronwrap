"""Integration helpers for running a PipelineConfig."""
from __future__ import annotations

from typing import Optional

from cronwrap.pipeline import PipelineConfig, PipelineResult, StepResult
from cronwrap.runner import run_command


def run_pipeline(cfg: PipelineConfig, timeout: Optional[float] = None) -> PipelineResult:
    """Execute each step in *cfg* and return a PipelineResult."""
    result = PipelineResult(label=cfg.label)

    for idx, cmd in enumerate(cfg.steps):
        run = run_command(cmd, timeout=timeout)
        step = StepResult(
            index=idx,
            command=cmd,
            exit_code=run.exit_code,
            stdout=run.stdout or "",
            stderr=run.stderr or "",
        )
        result.step_results.append(step)

        if not step.succeeded and cfg.stop_on_failure:
            result.aborted_at = idx
            break

    return result


def pipeline_summary(result: PipelineResult) -> str:
    lines = [str(result)]
    for sr in result.step_results:
        mark = "✓" if sr.succeeded else "✗"
        lines.append(f"  [{mark}] step {sr.index}: {sr.command}")
        if not sr.succeeded:
            lines.append(f"      exit_code={sr.exit_code}")
            if sr.stderr.strip():
                lines.append(f"      stderr: {sr.stderr.strip()[:200]}")
    if result.aborted_at is not None:
        lines.append(f"  Pipeline aborted after step {result.aborted_at}.")
    return "\n".join(lines)


def build_pipeline_config() -> PipelineConfig:
    return PipelineConfig.from_env()
