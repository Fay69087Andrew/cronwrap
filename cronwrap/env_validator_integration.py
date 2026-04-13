"""Helpers to integrate EnvValidator into the cronwrap run pipeline."""
from __future__ import annotations

import logging
from typing import Optional

from cronwrap.env_validator import EnvValidatorConfig, ValidationResult, validate_env

logger = logging.getLogger(__name__)


def check_env_or_abort(
    config: Optional[EnvValidatorConfig] = None,
) -> Optional[ValidationResult]:
    """Validate environment variables; return result or None if no config.

    Returns:
        ``ValidationResult`` when at least one required variable is configured,
        ``None`` when the config has no required variables (no-op).

    Raises:
        SystemExit(2): if any required variable is missing.
    """
    if config is None:
        config = EnvValidatorConfig.from_env()

    if not config.required:
        return None

    result = validate_env(config)

    if result.ok:
        logger.debug("EnvValidator: all %d required variable(s) present", len(config.required))
    else:
        logger.error(
            "EnvValidator: aborting — missing variables: %s",
            ", ".join(result.missing),
        )
        raise SystemExit(2)

    return result


def env_validation_summary(result: Optional[ValidationResult]) -> str:
    """Return a human-readable one-liner for log output."""
    if result is None:
        return "EnvValidation: skipped (no required vars configured)"
    return str(result)
