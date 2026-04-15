"""Tests for cronwrap.signal_handler."""
from __future__ import annotations

import signal
from unittest.mock import MagicMock, patch

import pytest

from cronwrap.signal_handler import (
    SignalHandlerConfig,
    SignalState,
    register_handlers,
    signal_summary,
)


class TestSignalHandlerConfig:
    def test_defaults(self):
        cfg = SignalHandlerConfig()
        assert cfg.handle_sigterm is True
        assert cfg.handle_sigint is True
        assert cfg.propagate_to_child is True

    def test_from_env_defaults(self):
        cfg = SignalHandlerConfig.from_env({})
        assert cfg.handle_sigterm is True
        assert cfg.handle_sigint is True
        assert cfg.propagate_to_child is True

    def test_from_env_disabled(self):
        cfg = SignalHandlerConfig.from_env(
            {
                "CRONWRAP_HANDLE_SIGTERM": "false",
                "CRONWRAP_HANDLE_SIGINT": "false",
                "CRONWRAP_SIGNAL_PROPAGATE": "false",
            }
        )
        assert cfg.handle_sigterm is False
        assert cfg.handle_sigint is False
        assert cfg.propagate_to_child is False

    def test_invalid_handle_sigterm_raises(self):
        with pytest.raises(TypeError):
            SignalHandlerConfig(handle_sigterm="yes")  # type: ignore[arg-type]

    def test_invalid_propagate_raises(self):
        with pytest.raises(TypeError):
            SignalHandlerConfig(propagate_to_child=1)  # type: ignore[arg-type]


class TestSignalState:
    def test_not_terminated_by_default(self):
        state = SignalState()
        assert state.terminated is False
        assert state.received is None

    def test_terminated_when_signal_set(self):
        state = SignalState(received=signal.SIGTERM)
        assert state.terminated is True
        assert state.received == signal.SIGTERM


class TestRegisterHandlers:
    def test_updates_state_on_signal(self):
        state = SignalState()
        cfg = SignalHandlerConfig()
        register_handlers(cfg, state)
        # Simulate signal delivery by calling the installed handler directly
        handler = signal.getsignal(signal.SIGTERM)
        handler(signal.SIGTERM, None)
        assert state.received == signal.SIGTERM

    def test_calls_extra_callback(self):
        state = SignalState()
        cfg = SignalHandlerConfig()
        cb = MagicMock()
        register_handlers(cfg, state, extra_callback=cb)
        handler = signal.getsignal(signal.SIGTERM)
        handler(signal.SIGTERM, None)
        cb.assert_called_once_with(signal.SIGTERM)

    def test_propagates_to_child(self):
        state = SignalState()
        cfg = SignalHandlerConfig(propagate_to_child=True)
        register_handlers(cfg, state, child_pid=99999)
        handler = signal.getsignal(signal.SIGTERM)
        with patch("os.kill") as mock_kill:
            handler(signal.SIGTERM, None)
            mock_kill.assert_called_once_with(99999, signal.SIGTERM)

    def test_no_propagation_when_disabled(self):
        state = SignalState()
        cfg = SignalHandlerConfig(propagate_to_child=False)
        register_handlers(cfg, state, child_pid=99999)
        handler = signal.getsignal(signal.SIGTERM)
        with patch("os.kill") as mock_kill:
            handler(signal.SIGTERM, None)
            mock_kill.assert_not_called()


class TestSignalSummary:
    def test_not_terminated(self):
        summary = signal_summary(SignalState())
        assert summary["terminated"] is False
        assert summary["signal"] is None

    def test_terminated(self):
        summary = signal_summary(SignalState(received=signal.SIGINT))
        assert summary["terminated"] is True
        assert summary["signal"] == signal.SIGINT
