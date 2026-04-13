"""Job execution history tracking for cronwrap."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

DEFAULT_HISTORY_FILE = os.path.expanduser("~/.cronwrap_history.json")
MAX_HISTORY_ENTRIES = 100


@dataclass
class HistoryEntry:
    command: str
    exit_code: int
    started_at: str
    duration_seconds: float
    attempts: int = 1
    stdout: str = ""
    stderr: str = ""

    @property
    def succeeded(self) -> bool:
        return self.exit_code == 0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "HistoryEntry":
        return cls(**data)


@dataclass
class HistoryStore:
    path: str = DEFAULT_HISTORY_FILE
    max_entries: int = MAX_HISTORY_ENTRIES
    _entries: List[HistoryEntry] = field(default_factory=list, repr=False)

    def load(self) -> None:
        """Load history entries from disk."""
        p = Path(self.path)
        if not p.exists():
            self._entries = []
            return
        try:
            raw = json.loads(p.read_text())
            self._entries = [HistoryEntry.from_dict(e) for e in raw]
        except (json.JSONDecodeError, TypeError, KeyError):
            self._entries = []

    def save(self) -> None:
        """Persist history entries to disk."""
        p = Path(self.path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps([e.to_dict() for e in self._entries], indent=2))

    def record(self, entry: HistoryEntry) -> None:
        """Append an entry and trim to max_entries."""
        self._entries.append(entry)
        if len(self._entries) > self.max_entries:
            self._entries = self._entries[-self.max_entries :]

    def entries(self) -> List[HistoryEntry]:
        return list(self._entries)

    def last(self, n: int = 10) -> List[HistoryEntry]:
        return self._entries[-n:]


def make_entry(
    command: str,
    exit_code: int,
    started_at: datetime,
    duration_seconds: float,
    attempts: int = 1,
    stdout: str = "",
    stderr: str = "",
) -> HistoryEntry:
    """Convenience factory for creating a HistoryEntry."""
    return HistoryEntry(
        command=command,
        exit_code=exit_code,
        started_at=started_at.astimezone(timezone.utc).isoformat(),
        duration_seconds=round(duration_seconds, 3),
        attempts=attempts,
        stdout=stdout,
        stderr=stderr,
    )
