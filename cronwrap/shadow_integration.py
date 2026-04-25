"""Integration helpers that wire ShadowConfig into the cronwrap run loop."""
from __future__ import annotations

import os
from typing import Optional, Tuple

from cronwrap.runner import RunResult, run_command
from cronwrap.shadow import ShadowConfig, ShadowResult, compare_results


def build_shadow_config(env: Optional[dict] = None) -> ShadowConfig:
    """Build a ShadowConfig from the process environment (or a supplied dict)."""
    return ShadowConfig.from_env(env if env is not None else dict(os.environ))


def run_shadow(
    cfg: ShadowConfig,
    primary_result: RunResult,
    timeout: Optional[float] = None,
) -> Optional[ShadowResult]:
    """Execute the shadow command and compare it against *primary_result*.

    Returns ``None`` when shadow mode is disabled.
    """
    if not cfg.enabled:
        return None

    shadow_result: RunResult = run_command(
        cfg.reference_command,
        timeout=timeout,
    )

    primary_stdout = (
        primary_result.stdout
        if isinstance(primary_result.stdout, bytes)
        else (primary_result.stdout or "").encode()
    )
    shadow_stdout = (
        shadow_result.stdout
        if isinstance(shadow_result.stdout, bytes)
        else (shadow_result.stdout or "").encode()
    )

    return compare_results(
        primary_stdout=primary_stdout,
        shadow_stdout=shadow_stdout,
        primary_exit=primary_result.exit_code,
        shadow_exit=shadow_result.exit_code,
        cfg=cfg,
    )


def shadow_report(result: Optional[ShadowResult]) -> str:
    """Return a human-readable one-line report for logging."""
    if result is None:
        return "shadow: disabled"
    return result.summary()
