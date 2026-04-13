"""Integration helpers that wire OutputCaptureConfig into the run pipeline."""
from __future__ import annotations

from cronwrap.output_capture import CapturedOutput, OutputCaptureConfig, decode_output
from cronwrap.runner import RunResult


def capture_from_result(
    result: RunResult,
    config: OutputCaptureConfig | None = None,
) -> CapturedOutput:
    """Decode the raw bytes stored on a RunResult into a CapturedOutput.

    If *config* is ``None`` the config is read from the environment.

    Parameters
    ----------
    result:
        A completed :class:`~cronwrap.runner.RunResult`.
    config:
        Optional explicit config; defaults to ``OutputCaptureConfig.from_env()``.

    Returns
    -------
    CapturedOutput
        Decoded, possibly-truncated output.
    """
    if config is None:
        config = OutputCaptureConfig.from_env()

    raw_stdout: bytes = result.stdout if isinstance(result.stdout, bytes) else b""
    raw_stderr: bytes = result.stderr if isinstance(result.stderr, bytes) else b""

    return decode_output(raw_stdout, raw_stderr, config)


def output_summary(captured: CapturedOutput, max_chars: int = 500) -> str:
    """Return a short human-readable summary of captured output.

    Parameters
    ----------
    captured:
        A :class:`~cronwrap.output_capture.CapturedOutput` instance.
    max_chars:
        Maximum characters to include in the summary before appending an
        ellipsis.  Must be positive.

    Returns
    -------
    str
        A summary string suitable for log messages or alert bodies.
    """
    if max_chars <= 0:
        raise ValueError(f"max_chars must be positive, got {max_chars}")

    text = captured.combined()
    if not text:
        return "(no output)"

    suffix = " ... [truncated]" if captured.truncated or len(text) > max_chars else ""
    return text[:max_chars] + suffix
