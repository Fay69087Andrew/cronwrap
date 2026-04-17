"""Job annotation support — attach freeform metadata to a run."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, Optional

_MAX_KEY_LEN = 64
_MAX_VAL_LEN = 256
_MAX_ENTRIES = 32


@dataclass
class AnnotationConfig:
    enabled: bool = True
    max_entries: int = _MAX_ENTRIES

    def __post_init__(self) -> None:
        if self.max_entries < 1:
            raise ValueError("max_entries must be >= 1")

    @classmethod
    def from_env(cls) -> "AnnotationConfig":
        enabled = os.environ.get("CRONWRAP_ANNOTATIONS_ENABLED", "true").lower() != "false"
        max_entries = int(os.environ.get("CRONWRAP_ANNOTATIONS_MAX_ENTRIES", str(_MAX_ENTRIES)))
        return cls(enabled=enabled, max_entries=max_entries)


@dataclass
class Annotations:
    config: AnnotationConfig = field(default_factory=AnnotationConfig)
    _data: Dict[str, str] = field(default_factory=dict, init=False, repr=False)

    def set(self, key: str, value: str) -> None:
        if not self.config.enabled:
            return
        key = str(key).strip()
        if not key:
            raise ValueError("Annotation key must not be empty")
        if len(key) > _MAX_KEY_LEN:
            raise ValueError(f"Annotation key too long (max {_MAX_KEY_LEN})")
        value = str(value)
        if len(value) > _MAX_VAL_LEN:
            raise ValueError(f"Annotation value too long (max {_MAX_VAL_LEN})")
        if key not in self._data and len(self._data) >= self.config.max_entries:
            raise ValueError(f"Annotation limit reached (max {self.config.max_entries})")
        self._data[key] = value

    def get(self, key: str) -> Optional[str]:
        return self._data.get(key)

    def to_dict(self) -> Dict[str, str]:
        return dict(self._data)

    def merge(self, other: Dict[str, str]) -> "Annotations":
        merged = Annotations(config=self.config)
        for k, v in {**self._data, **other}.items():
            merged.set(k, v)
        return merged

    def __len__(self) -> int:
        return len(self._data)

    def __repr__(self) -> str:
        return f"Annotations({self._data!r})"
