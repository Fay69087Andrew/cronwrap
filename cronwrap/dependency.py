"""Dependency check support for cronwrap.

Allows jobs to declare prerequisite commands or services that must
succeed before the main job runs.
"""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class DependencyConfig:
    """Configuration for pre-job dependency checks."""

    checks: List[str] = field(default_factory=list)
    timeout_seconds: int = 10
    enabled: bool = True

    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be a positive integer")

    @classmethod
    def from_env(cls) -> "DependencyConfig":
        raw = os.environ.get("CRONWRAP_DEP_CHECKS", "")
        checks = [c.strip() for c in raw.split(",") if c.strip()]
        timeout = int(os.environ.get("CRONWRAP_DEP_TIMEOUT", "10"))
        enabled = os.environ.get("CRONWRAP_DEP_ENABLED", "true").lower() != "false"
        return cls(checks=checks, timeout_seconds=timeout, enabled=enabled)


@dataclass
class DependencyResult:
    """Outcome of a single dependency check."""

    command: str
    exit_code: int
    stdout: str
    stderr: str

    @property
    def passed(self) -> bool:
        return self.exit_code == 0


def run_dependency_check(command: str, timeout: int) -> DependencyResult:
    """Run a single dependency check command and return its result."""
    try:
        proc = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return DependencyResult(
            command=command,
            exit_code=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
        )
    except subprocess.TimeoutExpired:
        return DependencyResult(
            command=command,
            exit_code=1,
            stdout="",
            stderr=f"Timed out after {timeout}s",
        )


def check_all(
    cfg: DependencyConfig,
) -> List[DependencyResult]:
    """Run all dependency checks and return results."""
    if not cfg.enabled:
        return []
    return [
        run_dependency_check(cmd, cfg.timeout_seconds)
        for cmd in cfg.checks
    ]


def all_passed(results: List[DependencyResult]) -> bool:
    """Return True only if every dependency check passed."""
    return all(r.passed for r in results)
