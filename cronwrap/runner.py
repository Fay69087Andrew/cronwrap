"""Core command runner module for cronwrap.

Handles executing shell commands, capturing output,
and returning structured result objects.
"""

import subprocess
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RunResult:
    """Result of a command execution."""
    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    started_at: float
    attempts: int = 1
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.exit_code == 0

    def __str__(self) -> str:
        status = "SUCCESS" if self.success else f"FAILED (exit {self.exit_code})"
        return (
            f"[{status}] command={self.command!r} "
            f"duration={self.duration_seconds:.2f}s attempts={self.attempts}"
        )


def run_command(
    command: str,
    timeout: Optional[int] = None,
    retries: int = 0,
    retry_delay: float = 5.0,
) -> RunResult:
    """Execute a shell command with optional retries.

    Args:
        command: Shell command string to execute.
        timeout: Optional timeout in seconds per attempt.
        retries: Number of additional attempts on failure (0 = no retry).
        retry_delay: Seconds to wait between retry attempts.

    Returns:
        RunResult with execution details.
    """
    attempts = 0
    max_attempts = retries + 1
    started_at = time.time()
    last_result: Optional[RunResult] = None

    while attempts < max_attempts:
        attempts += 1
        attempt_start = time.time()

        try:
            proc = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            duration = time.time() - attempt_start
            last_result = RunResult(
                command=command,
                exit_code=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
                duration_seconds=duration,
                started_at=started_at,
                attempts=attempts,
            )
        except subprocess.TimeoutExpired as exc:
            duration = time.time() - attempt_start
            last_result = RunResult(
                command=command,
                exit_code=-1,
                stdout="",
                stderr="",
                duration_seconds=duration,
                started_at=started_at,
                attempts=attempts,
                error=f"Timeout after {timeout}s",
            )

        if last_result.success:
            break

        if attempts < max_attempts:
            time.sleep(retry_delay)

    return last_result
