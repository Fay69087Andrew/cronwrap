"""Tests for cronwrap.tracer and cronwrap.tracer_integration."""
import time
import pytest

from cronwrap.tracer import Span, Tracer, TracerConfig
from cronwrap.tracer_integration import build_tracer, build_tracer_config, tracer_summary


class TestTracerConfig:
    def test_defaults(self):
        cfg = TracerConfig()
        assert cfg.enabled is True
        assert cfg.max_spans == 256

    def test_zero_max_spans_raises(self):
        with pytest.raises(ValueError, match="max_spans"):
            TracerConfig(max_spans=0)

    def test_negative_max_spans_raises(self):
        with pytest.raises(ValueError):
            TracerConfig(max_spans=-1)

    def test_from_env_defaults(self):
        cfg = TracerConfig.from_env({})
        assert cfg.enabled is True
        assert cfg.max_spans == 256

    def test_from_env_disabled(self):
        cfg = TracerConfig.from_env({"CRONWRAP_TRACER_ENABLED": "false"})
        assert cfg.enabled is False

    def test_from_env_custom_max_spans(self):
        cfg = TracerConfig.from_env({"CRONWRAP_TRACER_MAX_SPANS": "10"})
        assert cfg.max_spans == 10


class TestSpan:
    def test_duration_none_when_open(self):
        s = Span(name="test", start_time=time.time())
        assert s.duration is None

    def test_duration_computed(self):
        s = Span(name="test", start_time=1000.0, end_time=1001.5)
        assert s.duration == pytest.approx(1.5, abs=1e-5)

    def test_to_dict_keys(self):
        s = Span(name="x", start_time=1.0, end_time=2.0)
        d = s.to_dict()
        assert set(d.keys()) == {"name", "start_time", "end_time", "duration", "metadata"}


class TestTracer:
    def test_start_and_end_span(self):
        t = Tracer(TracerConfig())
        span = t.start_span("step1")
        time.sleep(0.01)
        t.end_span(span)
        assert span.duration is not None
        assert span.duration > 0

    def test_spans_recorded(self):
        t = Tracer(TracerConfig())
        s = t.start_span("a")
        t.end_span(s)
        assert len(t.spans()) == 1

    def test_max_spans_evicts_oldest(self):
        t = Tracer(TracerConfig(max_spans=2))
        for name in ["a", "b", "c"]:
            t.end_span(t.start_span(name))
        assert len(t.spans()) == 2
        assert t.spans()[0].name == "b"

    def test_disabled_tracer_does_not_record(self):
        t = Tracer(TracerConfig(enabled=False))
        t.end_span(t.start_span("x"))
        assert len(t.spans()) == 0

    def test_summary_keys(self):
        t = Tracer(TracerConfig())
        t.end_span(t.start_span("s"))
        s = t.summary()
        assert "total_spans" in s
        assert "total_duration" in s
        assert "spans" in s

    def test_metadata_stored(self):
        t = Tracer(TracerConfig())
        span = t.start_span("s", metadata={"job": "backup"})
        assert span.metadata["job"] == "backup"


class TestTracerIntegration:
    def test_build_tracer_returns_tracer(self):
        t = build_tracer(TracerConfig())
        assert isinstance(t, Tracer)

    def test_build_tracer_config_from_env(self):
        cfg = build_tracer_config({"CRONWRAP_TRACER_MAX_SPANS": "5"})
        assert cfg.max_spans == 5

    def test_tracer_summary_str(self):
        t = build_tracer(TracerConfig())
        t.end_span(t.start_span("init"))
        out = tracer_summary(t)
        assert "init" in out
        assert "span" in out
