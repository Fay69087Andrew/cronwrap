"""Integration helpers for enriching run context with dynamic tags."""
from __future__ import annotations

import os
from typing import Dict, Optional

from .tags import TagSet
from .runner import RunResult


def build_tags_from_env(prefix: str = "CRONWRAP_TAG_") -> TagSet:
    """Build a TagSet from environment variables with the given prefix.

    E.g. CRONWRAP_TAG_ENV=production -> {"env": "production"}
    """
    pairs: Dict[str, str] = {}
    for key, value in os.environ.items():
        if key.startswith(prefix):
            tag_key = key[len(prefix):].lower()
            if tag_key:
                pairs[tag_key] = value
    return TagSet(tags=pairs)


def enrich_tags_from_result(base: TagSet, result: RunResult) -> TagSet:
    """Return a new TagSet merging base tags with result-derived tags."""
    derived: Dict[str, str] = {
        "exit_code": str(result.exit_code),
        "status": "success" if result.success else "failure",
    }
    return base.merge(TagSet(tags=derived))


def tags_summary(tags: TagSet) -> str:
    """Return a human-readable summary of the tag set."""
    d = tags.to_dict()
    if not d:
        return "tags: (none)"
    parts = ", ".join(f"{k}={v}" for k, v in sorted(d.items()))
    return f"tags: {parts}"


def filter_tags(tags: TagSet, keys: list[str]) -> TagSet:
    """Return a new TagSet containing only the specified keys."""
    d = tags.to_dict()
    filtered = {k: v for k, v in d.items() if k in keys}
    return TagSet(tags=filtered)
