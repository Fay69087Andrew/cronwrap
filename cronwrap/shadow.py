"""Shadow mode: run a command silently and compare its output against a
reference result without affecting the real job outcome."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ShadowConfig:
    enabled: bool = False
    reference_command: str = ""
    compare_stdout: bool = True
    compare_exit_code: bool = True
    algorithm: str = "sha256"

    def __post_init__(self) -> None:
        self.algorithm = self.algorithm.lower()
        if self.algorithm not in hashlib.algorithms_guaranteed:
            raise ValueError(
                f"algorithm {self.algorithm!r} is not supported; "
                f"choose from {sorted(hashlib.algorithms_guaranteed)}"
            )
        if self.enabled and not self.reference_command.strip():
            raise ValueError("reference_command must not be empty when shadow mode is enabled")

    @classmethod
    def from_env(cls, env: dict) -> "ShadowConfig":
        enabled = env.get("CRONWRAP_SHADOW_ENABLED", "false").lower() == "true"
        return cls(
            enabled=enabled,
            reference_command=env.get("CRONWRAP_SHADOW_COMMAND", ""),
            compare_stdout=env.get("CRONWRAP_SHADOW_COMPARE_STDOUT", "true").lower() == "true",
            compare_exit_code=env.get("CRONWRAP_SHADOW_COMPARE_EXIT_CODE", "true").lower() == "true",
            algorithm=env.get("CRONWRAP_SHADOW_ALGORITHM", "sha256"),
        )


@dataclass
class ShadowResult:
    primary_exit_code: int
    shadow_exit_code: int
    primary_stdout_hash: str
    shadow_stdout_hash: str
    stdout_match: bool
    exit_code_match: bool
    diverged: bool = field(init=False)

    def __post_init__(self) -> None:
        self.diverged = not self.stdout_match or not self.exit_code_match

    def summary(self) -> str:
        parts = [
            f"primary_exit={self.primary_exit_code}",
            f"shadow_exit={self.shadow_exit_code}",
            f"stdout_match={self.stdout_match}",
            f"exit_code_match={self.exit_code_match}",
            f"diverged={self.diverged}",
        ]
        return "shadow: " + ", ".join(parts)


def _hash(data: Optional[bytes], algorithm: str) -> str:
    if not data:
        return ""
    h = hashlib.new(algorithm)
    h.update(data)
    return h.hexdigest()


def compare_results(
    primary_stdout: Optional[bytes],
    shadow_stdout: Optional[bytes],
    primary_exit: int,
    shadow_exit: int,
    cfg: ShadowConfig,
) -> ShadowResult:
    primary_hash = _hash(primary_stdout, cfg.algorithm) if cfg.compare_stdout else ""
    shadow_hash = _hash(shadow_stdout, cfg.algorithm) if cfg.compare_stdout else ""
    stdout_match = (primary_hash == shadow_hash) if cfg.compare_stdout else True
    exit_code_match = (primary_exit == shadow_exit) if cfg.compare_exit_code else True
    return ShadowResult(
        primary_exit_code=primary_exit,
        shadow_exit_code=shadow_exit,
        primary_stdout_hash=primary_hash,
        shadow_stdout_hash=shadow_hash,
        stdout_match=stdout_match,
        exit_code_match=exit_code_match,
    )
