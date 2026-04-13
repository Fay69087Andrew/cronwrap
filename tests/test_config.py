"""Tests for cronwrap.config module."""

import pytest
from unittest.mock import patch

from cronwrap.config import CronwrapConfig, load_config_from_env


class TestCronwrapConfig:
    def test_defaults(self):
        cfg = CronwrapConfig()
        assert cfg.job_name == "cronwrap-job"
        assert cfg.max_attempts == 1
        assert cfg.retry_delay == 0.0
        assert cfg.log_file is None
        assert cfg.log_level == "INFO"
        assert cfg.alert_on_failure is False

    def test_log_level_uppercased(self):
        cfg = CronwrapConfig(log_level="debug")
        assert cfg.log_level == "DEBUG"

    def test_invalid_max_attempts_raises(self):
        with pytest.raises(ValueError, match="max_attempts"):
            CronwrapConfig(max_attempts=0)

    def test_invalid_retry_delay_raises(self):
        with pytest.raises(ValueError, match="retry_delay"):
            CronwrapConfig(retry_delay=-1.0)

    def test_custom_values(self):
        cfg = CronwrapConfig(
            job_name="backup",
            max_attempts=3,
            retry_delay=5.0,
            log_file="/var/log/cron.log",
            alert_on_failure=True,
            alert_to="admin@example.com",
        )
        assert cfg.job_name == "backup"
        assert cfg.max_attempts == 3
        assert cfg.retry_delay == 5.0
        assert cfg.alert_on_failure is True


class TestLoadConfigFromEnv:
    def test_defaults_when_no_env(self):
        with patch.dict("os.environ", {}, clear=False):
            cfg = load_config_from_env()
        assert cfg.max_attempts == 1
        assert cfg.log_level == "INFO"
        assert cfg.alert_on_failure is False

    def test_reads_env_values(self):
        env = {
            "CRONWRAP_JOB_NAME": "nightly-backup",
            "CRONWRAP_MAX_ATTEMPTS": "3",
            "CRONWRAP_RETRY_DELAY": "2.5",
            "CRONWRAP_LOG_LEVEL": "warning",
            "CRONWRAP_ALERT_ON_FAILURE": "true",
            "CRONWRAP_ALERT_TO": "ops@example.com",
        }
        with patch.dict("os.environ", env):
            cfg = load_config_from_env()
        assert cfg.job_name == "nightly-backup"
        assert cfg.max_attempts == 3
        assert cfg.retry_delay == 2.5
        assert cfg.log_level == "WARNING"
        assert cfg.alert_on_failure is True
        assert cfg.alert_to == "ops@example.com"

    def test_alert_on_failure_truthy_variants(self):
        for val in ("1", "true", "yes", "True", "YES"):
            with patch.dict("os.environ", {"CRONWRAP_ALERT_ON_FAILURE": val}):
                cfg = load_config_from_env()
            assert cfg.alert_on_failure is True, f"Failed for value: {val!r}"

    def test_alert_on_failure_false_variants(self):
        for val in ("0", "false", "no", ""):
            with patch.dict("os.environ", {"CRONWRAP_ALERT_ON_FAILURE": val}):
                cfg = load_config_from_env()
            assert cfg.alert_on_failure is False, f"Failed for value: {val!r}"
