"""Tag support for cronwrap jobs — attach arbitrary key/value labels to runs."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Dict, Optional

_TAG_RE = re.compile(r'^[a-zA-Z0-9_\-]{1,64}$')


@dataclass
class TagSet:
    """An immutable collection of key/value string tags attached to a job run."""

    tags: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for key, value in self.tags.items():
            if not _TAG_RE.match(key):
                raise ValueError(
                    f"Invalid tag key {key!r}: must match [a-zA-Z0-9_\\-]{{1,64}}"
                )
            if len(str(value)) > 256:
                raise ValueError(
                    f"Tag value for {key!r} exceeds 256 characters."
                )
        # Normalise all values to strings
        self.tags = {k: str(v) for k, v in self.tags.items()}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        return self.tags.get(key, default)

    def to_dict(self) -> Dict[str, str]:
        return dict(self.tags)

    def merge(self, other: "TagSet") -> "TagSet":
        """Return a new TagSet with *other* overriding keys in *self*."""
        merged = {**self.tags, **other.tags}
        return TagSet(tags=merged)

    def __repr__(self) -> str:  # pragma: no cover
        return f"TagSet({self.tags!r})"


def from_env(prefix: str = "CRONWRAP_TAG_") -> TagSet:
    """Build a TagSet from environment variables.

    Any env var whose name starts with *prefix* (default ``CRONWRAP_TAG_``) is
    collected.  The tag key is the suffix after the prefix, lower-cased.

    Example::

        CRONWRAP_TAG_ENV=production
        CRONWRAP_TAG_TEAM=platform
    """
    tags: Dict[str, str] = {}
    for name, value in os.environ.items():
        if name.startswith(prefix):
            key = name[len(prefix):].lower()
            if key:
                tags[key] = value
    return TagSet(tags=tags)


def parse_tags(raw: str) -> TagSet:
    """Parse a comma-separated ``key=value`` string into a TagSet.

    Example::

        parse_tags("env=prod,team=platform")
    """
    tags: Dict[str, str] = {}
    for pair in raw.split(","):
        pair = pair.strip()
        if not pair:
            continue
        if "=" not in pair:
            raise ValueError(f"Tag pair {pair!r} is missing '='")
        key, _, value = pair.partition("=")
        tags[key.strip()] = value.strip()
    return TagSet(tags=tags)
