"""Integration helpers that apply PrefixConfig to RunResult output."""
from __future__ import annotations

import os
from cronwrap.prefix import PrefixConfig, prefix_lines, prefix_summary


def build_prefix_config() -> PrefixConfig:
    """Build a PrefixConfig from environment variables."""
    return PrefixConfig.from_env()


def apply_prefix_to_output(stdout: str, stderr: str, cfg: PrefixConfig) -> tuple[str, str]:
    """Return (stdout, stderr) with each line prefixed according to *cfg*."""
    return prefix_lines(stdout, cfg), prefix_lines(stderr, cfg)


def apply_prefix_to_result(result, cfg: PrefixConfig):
    """Return a copy-like dict with prefixed stdout/stderr from a RunResult."""
    stdout = getattr(result, "stdout", "") or ""
    stderr = getattr(result, "stderr", "") or ""
    if isinstance(stdout, bytes):
        stdout = stdout.decode("utf-8", errors="replace")
    if isinstance(stderr, bytes):
        stderr = stderr.decode("utf-8", errors="replace")
    return {
        "stdout": prefix_lines(stdout, cfg),
        "stderr": prefix_lines(stderr, cfg),
        "exit_code": getattr(result, "exit_code", None),
        "command": getattr(result, "command", ""),
    }


def report_prefix(cfg: PrefixConfig) -> str:
    s = prefix_summary(cfg)
    status = "enabled" if s["enabled"] else "disabled"
    return (
        f"prefix: {status}, template={s['template']!r}, "
        f"job={s['job_name']!r}, timestamp={s['include_timestamp']}"
    )
