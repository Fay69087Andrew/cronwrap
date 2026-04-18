"""PagerDuty / generic on-call paging integration for cronwrap."""
from __future__ import annotations

import os
import urllib.request
import urllib.error
import json
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PagerConfig:
    enabled: bool = False
    routing_key: str = ""
    source: str = "cronwrap"
    severity: str = "error"  # critical | error | warning | info
    timeout: int = 10

    def __post_init__(self) -> None:
        self.severity = self.severity.lower()
        valid = {"critical", "error", "warning", "info"}
        if self.severity not in valid:
            raise ValueError(f"severity must be one of {valid}, got {self.severity!r}")
        if self.timeout <= 0:
            raise ValueError("timeout must be positive")
        if self.enabled and not self.routing_key:
            raise ValueError("routing_key is required when pager is enabled")

    @classmethod
    def from_env(cls) -> "PagerConfig":
        enabled = os.environ.get("CRONWRAP_PAGER_ENABLED", "false").lower() == "true"
        return cls(
            enabled=enabled,
            routing_key=os.environ.get("CRONWRAP_PAGER_ROUTING_KEY", ""),
            source=os.environ.get("CRONWRAP_PAGER_SOURCE", "cronwrap"),
            severity=os.environ.get("CRONWRAP_PAGER_SEVERITY", "error"),
            timeout=int(os.environ.get("CRONWRAP_PAGER_TIMEOUT", "10")),
        )


@dataclass
class PagerEvent:
    summary: str
    source: str
    severity: str
    custom_details: dict = field(default_factory=dict)

    def to_payload(self, routing_key: str) -> dict:
        return {
            "routing_key": routing_key,
            "event_action": "trigger",
            "payload": {
                "summary": self.summary,
                "source": self.source,
                "severity": self.severity,
                "custom_details": self.custom_details,
            },
        }


PD_EVENTS_URL = "https://events.pagerduty.com/v2/enqueue"


def send_page(config: PagerConfig, event: PagerEvent) -> Optional[str]:
    """Send event to PagerDuty. Returns dedup_key on success or None if disabled."""
    if not config.enabled:
        return None
    payload = json.dumps(event.to_payload(config.routing_key)).encode()
    req = urllib.request.Request(
        PD_EVENTS_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=config.timeout) as resp:
        body = json.loads(resp.read())
    return body.get("dedup_key")
