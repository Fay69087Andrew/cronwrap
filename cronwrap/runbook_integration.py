"""Integration helpers that attach runbook links to alert payloads."""
from __future__ import annotations

from typing import Dict, Any, Optional

from cronwrap.runbook import RunbookConfig, format_runbook_line, runbook_summary


def enrich_alert_context(
    context: Dict[str, Any],
    cfg: RunbookConfig,
) -> Dict[str, Any]:
    """Return a copy of *context* with a 'runbook' key added when available.

    The value is the formatted Markdown link, or None if not configured.
    The original dict is not mutated.
    """
    enriched = dict(context)
    enriched["runbook"] = format_runbook_line(cfg)
    return enriched


def append_runbook_to_body(body: str, cfg: RunbookConfig) -> str:
    """Append a runbook footer to an email/alert body string.

    If the runbook is not configured the original *body* is returned unchanged.
    """
    link = format_runbook_line(cfg)
    if link is None:
        return body
    separator = "\n\n---\n"
    return f"{body}{separator}Runbook: {link}"


def build_runbook_from_env() -> RunbookConfig:
    """Convenience factory — reads config entirely from the environment."""
    return RunbookConfig.from_env()


def runbook_report(cfg: RunbookConfig) -> str:
    """Return a multi-line diagnostic report string for the runbook config."""
    lines = [
        "=== Runbook Configuration ===",
        f"  enabled : {cfg.enabled}",
        f"  title   : {cfg.title!r}",
        f"  url     : {cfg.url!r}",
        f"  summary : {runbook_summary(cfg)}",
    ]
    return "\n".join(lines)
