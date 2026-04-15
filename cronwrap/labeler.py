"""Job labeling — attach key/value labels to a run for filtering and reporting."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Dict, Optional

_LABEL_KEY_RE = re.compile(r'^[a-z][a-z0-9_.-]{0,62}$')
_MAX_VALUE_LEN = 256


@dataclass
class LabelSet:
    """Immutable-ish collection of string labels attached to a job run."""
    labels: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        validated: Dict[str, str] = {}
        for k, v in self.labels.items():
            k = str(k)
            v = str(v)
            if not _LABEL_KEY_RE.match(k):
                raise ValueError(
                    f"Invalid label key {k!r}: must match [a-z][a-z0-9_.-]{{0,62}}"
                )
            if len(v) > _MAX_VALUE_LEN:
                raise ValueError(
                    f"Label value for {k!r} exceeds {_MAX_VALUE_LEN} characters."
                )
            validated[k] = v
        self.labels = validated

    def get(self, key: str) -> Optional[str]:
        return self.labels.get(key)

    def to_dict(self) -> Dict[str, str]:
        return dict(self.labels)

    def merge(self, other: "LabelSet") -> "LabelSet":
        """Return a new LabelSet with other's labels overriding self's."""
        merged = {**self.labels, **other.labels}
        return LabelSet(labels=merged)

    def __len__(self) -> int:
        return len(self.labels)

    def __repr__(self) -> str:  # pragma: no cover
        return f"LabelSet({self.labels!r})"


def from_env(prefix: str = "CRONWRAP_LABEL_") -> LabelSet:
    """Build a LabelSet from environment variables with the given prefix.

    E.g. CRONWRAP_LABEL_ENV=production  ->  label 'env' = 'production'
    """
    labels: Dict[str, str] = {}
    for key, value in os.environ.items():
        if key.startswith(prefix):
            label_key = key[len(prefix):].lower().replace("-", "_")
            if _LABEL_KEY_RE.match(label_key):
                labels[label_key] = value
    return LabelSet(labels=labels)


def label_summary(label_set: LabelSet) -> str:
    """Return a human-readable summary line of all labels."""
    if not label_set.labels:
        return "labels: (none)"
    pairs = ", ".join(f"{k}={v}" for k, v in sorted(label_set.labels.items()))
    return f"labels: {pairs}"
