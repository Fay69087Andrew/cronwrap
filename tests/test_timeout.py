"""Tests for cronwrap.timeout."""

from __future__ import annotations

import signal
import time
import pytest

from cronwrap.timeout import TimeoutConfig, TimeoutExpired, timeout_context


# ---------------------------------------------------------------------------
# TimeoutConfig
# ---------------------------------------------------------------------------

class TestTimeoutConfig:
    def test_defaults(self):
        cfg = TimeoutConfig()
        assert cfg.seconds is None
        assert cfg.kill_on_expire is True

    def test_valid_seconds(self):
        cfg = TimeoutConfig(seconds=30)
        assert cfg.seconds == 30

    def test_zero_seconds_raises(self):
        with pytest.raises(ValueError, match="positive integer"):
            TimeoutConfig(seconds=0)

    def test_negative_seconds_raises(self):
        with pytest.raises(ValueError, match="positive integer"):
            TimeoutConfig(seconds=-5)

    def test_from_env_no_timeout(self):
        cfg = TimeoutConfig.from_env({})
        assert cfg.seconds is None

    def test_from_env_with_timeout(self):
        cfg = TimeoutConfig.from_env({"CRONWRAP_TIMEOUT": "60"})
        assert cfg.seconds == 60

    def test_from_env_zero_means_no_timeout(self):
        cfg = TimeoutConfig.from_env({"CRONWRAP_TIMEOUT": "0"})
        assert cfg.seconds is None

    def test_from_env_kill_disabled(self):
        cfg = TimeoutConfig.from_env({"CRONWRAP_TIMEOUT": "10", "CRONWRAP_TIMEOUT_KILL": "0"})
        assert cfg.kill_on_expire is False

    def test_from_env_kill_enabled_by_default(self):
        cfg = TimeoutConfig.from_env({"CRONWRAP_TIMEOUT": "10"})
        assert cfg.kill_on_expire is True


# ---------------------------------------------------------------------------
# TimeoutExpired
# ---------------------------------------------------------------------------

class TestTimeoutExpired:
    def test_message_contains_seconds(self):
        exc = TimeoutExpired(45)
        assert "45" in str(exc)
        assert exc.seconds == 45


# ---------------------------------------------------------------------------
# timeout_context
# ---------------------------------------------------------------------------

class TestTimeoutContext:
    def test_no_timeout_does_not_raise(self):
        cfg = TimeoutConfig(seconds=None)
        with timeout_context(cfg):
            time.sleep(0)  # fast no-op

    def test_context_restores_previous_alarm(self):
        cfg = TimeoutConfig(seconds=10)
        with timeout_context(cfg):
            pass
        # After exiting, alarm should be cancelled (returns 0)
        remaining = signal.alarm(0)
        assert remaining == 0

    def test_timeout_fires_on_slow_code(self):
        cfg = TimeoutConfig(seconds=1)
        with pytest.raises(TimeoutExpired) as exc_info:
            with timeout_context(cfg):
                time.sleep(5)  # will be interrupted
        assert exc_info.value.seconds == 1

    def test_no_exception_when_fast_enough(self):
        cfg = TimeoutConfig(seconds=5)
        with timeout_context(cfg):
            pass  # completes immediately
