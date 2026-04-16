"""Pre-flight checks that run before the main cron job executes."""
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from typing import Callable, List, Optional


@dataclass
class PrecheckConfig:
    """Configuration for pre-flight checks."""

    enabled: bool = True
    abort_on_failure: bool = True
    checks: List[str] = field(default_factory=list)  # names of built-in checks

    def __post_init__(self) -> None:
        self.checks = [c.strip().lower() for c in self.checks if c.strip()]

    @classmethod
    def from_env(cls) -> "PrecheckConfig":
        enabled = os.environ.get("CRONWRAP_PRECHECK_ENABLED", "true").lower() != "false"
        abort = os.environ.get("CRONWRAP_PRECHECK_ABORT_ON_FAILURE", "true").lower() != "false"
        raw = os.environ.get("CRONWRAP_PRECHECK_CHECKS", "")
        checks = [c for c in raw.split(",") if c.strip()] if raw.strip() else []
        return cls(enabled=enabled, abort_on_failure=abort, checks=checks)


@dataclass
class PrecheckResult:
    name: str
    passed: bool
    message: str = ""

    def __str__(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        msg = f" — {self.message}" if self.message else ""
        return f"[{status}] {self.name}{msg}"


def _check_disk_space() -> PrecheckResult:
    """Fail if free disk space on / is below 100 MB."""
    stat = shutil.disk_usage("/")
    free_mb = stat.free / (1024 * 1024)
    if free_mb < 100:
        return PrecheckResult("disk_space", False, f"{free_mb:.1f} MB free (need ≥ 100 MB)")
    return PrecheckResult("disk_space", True, f"{free_mb:.1f} MB free")


def _check_tmp_writable() -> PrecheckResult:
    """Fail if /tmp is not writable."""
    writable = os.access("/tmp", os.W_OK)
    return PrecheckResult(
        "tmp_writable",
        writable,
        "/tmp is writable" if writable else "/tmp is not writable",
    )


_BUILTIN_CHECKS: dict[str, Callable[[], PrecheckResult]] = {
    "disk_space": _check_disk_space,
    "tmp_writable": _check_tmp_writable,
}


def run_prechecks(
    config: PrecheckConfig,
    extra: Optional[List[Callable[[], PrecheckResult]]] = None,
) -> List[PrecheckResult]:
    """Run all configured pre-flight checks and return results."""
    if not config.enabled:
        return []

    results: List[PrecheckResult] = []

    for name in config.checks:
        fn = _BUILTIN_CHECKS.get(name)
        if fn is None:
            results.append(PrecheckResult(name, False, "unknown built-in check"))
        else:
            results.append(fn())

    for fn in extra or []:
        results.append(fn())

    return results


def precheck_summary(results: List[PrecheckResult]) -> str:
    """Return a human-readable summary of precheck results."""
    if not results:
        return "No pre-flight checks ran."
    lines = [str(r) for r in results]
    failed = sum(1 for r in results if not r.passed)
    lines.append(f"{len(results)} check(s), {failed} failed.")
    return "\n".join(lines)
