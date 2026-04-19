"""Integration helpers: apply TrimmerConfig to RunResult output."""
from __future__ import annotations

from cronwrap.trimmer import TrimmerConfig, trim_output, trimmer_summary


def build_trimmer_config() -> TrimmerConfig:
    """Build a TrimmerConfig from environment variables."""
    return TrimmerConfig.from_env()


def trim_result_output(
    stdout: str,
    stderr: str,
    cfg: TrimmerConfig | None = None,
) -> tuple[str, str]:
    """Return (trimmed_stdout, trimmed_stderr) according to *cfg*."""
    if cfg is None:
        cfg = TrimmerConfig()
    return trim_output(stdout, cfg), trim_output(stderr, cfg)


def apply_trimmer(result_stdout: str, result_stderr: str) -> dict:
    """Convenience: build config from env, trim, return summary dict."""
    cfg = build_trimmer_config()
    trimmed_out, trimmed_err = trim_result_output(result_stdout, result_stderr, cfg)
    summary = trimmer_summary(cfg)
    summary["stdout"] = trimmed_out
    summary["stderr"] = trimmed_err
    return summary
