"""Integration helpers for dependency checks in the cronwrap pipeline."""
from __future__ import annotations

import sys
from typing import List, Optional

from cronwrap.dependency import (
    DependencyConfig,
    DependencyResult,
    all_passed,
    check_all,
)


def build_dependency_config() -> DependencyConfig:
    """Build a DependencyConfig from environment variables."""
    return DependencyConfig.from_env()


def run_dependency_checks_or_abort(cfg: DependencyConfig) -> List[DependencyResult]:
    """Run all dependency checks; abort (sys.exit) if any fail."""
    results = check_all(cfg)
    if results and not all_passed(results):
        failed = [r for r in results if not r.passed]
        lines = ["[cronwrap] Dependency checks failed:"]
        for r in failed:
            lines.append(f"  command: {r.command!r}")
            lines.append(f"  exit_code: {r.exit_code}")
            if r.stderr.strip():
                lines.append(f"  stderr: {r.stderr.strip()}")
        print("\n".join(lines), file=sys.stderr)
        sys.exit(1)
    return results


def dependency_summary(results: List[DependencyResult]) -> str:
    """Return a human-readable summary of dependency check results."""
    if not results:
        return "dependency_checks: none"
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    lines = [f"dependency_checks: {passed}/{total} passed"]
    for r in results:
        status = "OK" if r.passed else "FAIL"
        lines.append(f"  [{status}] {r.command}")
    return "\n".join(lines)
