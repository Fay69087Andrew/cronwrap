"""Output fingerprinting — detect whether a job's output has changed between runs."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

_ALGORITHMS = {"md5", "sha1", "sha256"}
_DEFAULT_STATE_DIR = "/tmp/cronwrap/fingerprints"


@dataclass
class FingerprintConfig:
    enabled: bool = True
    algorithm: str = "sha256"
    state_dir: str = _DEFAULT_STATE_DIR

    def __post_init__(self) -> None:
        self.algorithm = self.algorithm.lower()
        if self.algorithm not in _ALGORITHMS:
            raise ValueError(
                f"algorithm must be one of {sorted(_ALGORITHMS)}, got {self.algorithm!r}"
            )
        if not self.state_dir:
            raise ValueError("state_dir must not be empty")

    @classmethod
    def from_env(cls) -> "FingerprintConfig":
        enabled = os.environ.get("CRONWRAP_FINGERPRINT_ENABLED", "true").lower() != "false"
        algorithm = os.environ.get("CRONWRAP_FINGERPRINT_ALGORITHM", "sha256")
        state_dir = os.environ.get("CRONWRAP_FINGERPRINT_STATE_DIR", _DEFAULT_STATE_DIR)
        return cls(enabled=enabled, algorithm=algorithm, state_dir=state_dir)


@dataclass
class Fingerprint:
    job_id: str
    digest: str
    algorithm: str
    recorded_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "digest": self.digest,
            "algorithm": self.algorithm,
            "recorded_at": self.recorded_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Fingerprint":
        return cls(
            job_id=data["job_id"],
            digest=data["digest"],
            algorithm=data["algorithm"],
            recorded_at=datetime.fromisoformat(data["recorded_at"]),
        )


def compute_fingerprint(text: str, algorithm: str = "sha256") -> str:
    """Return hex digest of *text* using *algorithm*."""
    h = hashlib.new(algorithm)
    h.update(text.encode("utf-8", errors="replace"))
    return h.hexdigest()


def _state_path(state_dir: str, job_id: str) -> Path:
    safe = job_id.replace(os.sep, "_").replace(" ", "_")
    return Path(state_dir) / f"{safe}.json"


def load_fingerprint(cfg: FingerprintConfig, job_id: str) -> Optional[Fingerprint]:
    """Load the stored fingerprint for *job_id*, or None if absent."""
    path = _state_path(cfg.state_dir, job_id)
    if not path.exists():
        return None
    with path.open() as fh:
        return Fingerprint.from_dict(json.load(fh))


def save_fingerprint(cfg: FingerprintConfig, fp: Fingerprint) -> None:
    """Persist *fp* to disk."""
    path = _state_path(cfg.state_dir, fp.job_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as fh:
        json.dump(fp.to_dict(), fh)


def output_changed(cfg: FingerprintConfig, job_id: str, output: str) -> bool:
    """Return True when *output* differs from the last recorded fingerprint."""
    if not cfg.enabled:
        return True
    current = compute_fingerprint(output, cfg.algorithm)
    previous = load_fingerprint(cfg, job_id)
    return previous is None or previous.digest != current


def fingerprint_summary(cfg: FingerprintConfig, job_id: str, output: str) -> dict:
    """Record a new fingerprint and return a summary dict."""
    digest = compute_fingerprint(output, cfg.algorithm)
    previous = load_fingerprint(cfg, job_id)
    changed = previous is None or previous.digest != digest
    fp = Fingerprint(job_id=job_id, digest=digest, algorithm=cfg.algorithm)
    if cfg.enabled:
        save_fingerprint(cfg, fp)
    return {
        "job_id": job_id,
        "algorithm": cfg.algorithm,
        "digest": digest,
        "changed": changed,
        "previous_digest": previous.digest if previous else None,
    }
