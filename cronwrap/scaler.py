"""Dynamic concurrency scaler based on recent job duration trends."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List
import os


@dataclass
class ScalerConfig:
    enabled: bool = True
    min_instances: int = 1
    max_instances: int = 4
    target_duration_seconds: float = 60.0
    scale_up_threshold: float = 1.5   # ratio: actual / target
    scale_down_threshold: float = 0.5
    window: int = 5  # number of recent durations to consider

    def __post_init__(self) -> None:
        if self.min_instances < 1:
            raise ValueError("min_instances must be >= 1")
        if self.max_instances < self.min_instances:
            raise ValueError("max_instances must be >= min_instances")
        if self.target_duration_seconds <= 0:
            raise ValueError("target_duration_seconds must be > 0")
        if self.scale_up_threshold <= 1.0:
            raise ValueError("scale_up_threshold must be > 1.0")
        if not (0.0 < self.scale_down_threshold < 1.0):
            raise ValueError("scale_down_threshold must be between 0 and 1")
        if self.window < 1:
            raise ValueError("window must be >= 1")

    @classmethod
    def from_env(cls) -> "ScalerConfig":
        return cls(
            enabled=os.environ.get("CRONWRAP_SCALER_ENABLED", "true").lower() == "true",
            min_instances=int(os.environ.get("CRONWRAP_SCALER_MIN", "1")),
            max_instances=int(os.environ.get("CRONWRAP_SCALER_MAX", "4")),
            target_duration_seconds=float(os.environ.get("CRONWRAP_SCALER_TARGET", "60")),
            scale_up_threshold=float(os.environ.get("CRONWRAP_SCALER_UP_THRESHOLD", "1.5")),
            scale_down_threshold=float(os.environ.get("CRONWRAP_SCALER_DOWN_THRESHOLD", "0.5")),
            window=int(os.environ.get("CRONWRAP_SCALER_WINDOW", "5")),
        )


@dataclass
class ScaleDecision:
    recommended_instances: int
    reason: str
    avg_duration: float
    current_instances: int

    def __str__(self) -> str:
        return (
            f"ScaleDecision(recommended={self.recommended_instances}, "
            f"current={self.current_instances}, avg_duration={self.avg_duration:.2f}s, "
            f"reason={self.reason})"
        )


def evaluate_scale(
    cfg: ScalerConfig,
    durations: List[float],
    current_instances: int,
) -> ScaleDecision:
    """Return a scaling recommendation based on recent durations."""
    if not cfg.enabled or not durations:
        return ScaleDecision(current_instances, "no-op", 0.0, current_instances)

    recent = durations[-cfg.window :]
    avg = sum(recent) / len(recent)
    ratio = avg / cfg.target_duration_seconds

    if ratio >= cfg.scale_up_threshold:
        recommended = min(current_instances + 1, cfg.max_instances)
        reason = "scale-up"
    elif ratio <= cfg.scale_down_threshold:
        recommended = max(current_instances - 1, cfg.min_instances)
        reason = "scale-down"
    else:
        recommended = current_instances
        reason = "stable"

    return ScaleDecision(recommended, reason, avg, current_instances)


def scaler_summary(decision: ScaleDecision) -> str:
    return (
        f"scaler: {decision.reason} | avg={decision.avg_duration:.1f}s "
        f"current={decision.current_instances} recommended={decision.recommended_instances}"
    )
