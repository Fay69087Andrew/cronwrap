"""Integration helpers for the execution tracer."""
from __future__ import annotations

import os
from typing import Optional

from cronwrap.tracer import Tracer, TracerConfig


def build_tracer_config(env: Optional[dict] = None) -> TracerConfig:
    return TracerConfig.from_env(env if env is not None else dict(os.environ))


def build_tracer(config: Optional[TracerConfig] = None) -> Tracer:
    if config is None:
        config = build_tracer_config()
    return Tracer(config)


def tracer_summary(tracer: Tracer) -> str:
    summary = tracer.summary()
    lines = [
        f"Tracer: {summary['total_spans']} span(s), "
        f"total duration {summary['total_duration']:.3f}s"
    ]
    for span in summary["spans"]:
        dur = f"{span['duration']:.3f}s" if span["duration"] is not None else "open"
        lines.append(f"  [{dur}] {span['name']}")
    return "\n".join(lines)
