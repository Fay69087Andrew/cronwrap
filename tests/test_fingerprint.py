"""Tests for cronwrap.fingerprint and cronwrap.fingerprint_integration."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from cronwrap.fingerprint import (
    Fingerprint,
    FingerprintConfig,
    compute_fingerprint,
    fingerprint_summary,
    load_fingerprint,
    output_changed,
    save_fingerprint,
)
from cronwrap.fingerprint_integration import (
    check_output_changed,
    fingerprint_report,
    record_fingerprint,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _result(stdout: str = "", stderr: str = "") -> MagicMock:
    r = MagicMock()
    r.stdout = stdout
    r.stderr = stderr
    return r


def _cfg(tmp_path: Path, algorithm: str = "sha256") -> FingerprintConfig:
    return FingerprintConfig(state_dir=str(tmp_path), algorithm=algorithm)


# ---------------------------------------------------------------------------
# TestFingerprintConfig
# ---------------------------------------------------------------------------

class TestFingerprintConfig:
    def test_defaults(self):
        cfg = FingerprintConfig()
        assert cfg.enabled is True
        assert cfg.algorithm == "sha256"
        assert cfg.state_dir

    def test_algorithm_lowercased(self):
        cfg = FingerprintConfig(algorithm="SHA256")
        assert cfg.algorithm == "sha256"

    def test_invalid_algorithm_raises(self):
        with pytest.raises(ValueError, match="algorithm"):
            FingerprintConfig(algorithm="crc32")

    def test_empty_state_dir_raises(self):
        with pytest.raises(ValueError, match="state_dir"):
            FingerprintConfig(state_dir="")

    def test_from_env_defaults(self, monkeypatch):
        for k in ("CRONWRAP_FINGERPRINT_ENABLED", "CRONWRAP_FINGERPRINT_ALGORITHM",
                  "CRONWRAP_FINGERPRINT_STATE_DIR"):
            monkeypatch.delenv(k, raising=False)
        cfg = FingerprintConfig.from_env()
        assert cfg.enabled is True
        assert cfg.algorithm == "sha256"

    def test_from_env_disabled(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_FINGERPRINT_ENABLED", "false")
        cfg = FingerprintConfig.from_env()
        assert cfg.enabled is False


# ---------------------------------------------------------------------------
# TestComputeFingerprint
# ---------------------------------------------------------------------------

class TestComputeFingerprint:
    def test_sha256_returns_64_hex_chars(self):
        assert len(compute_fingerprint("hello", "sha256")) == 64

    def test_md5_returns_32_hex_chars(self):
        assert len(compute_fingerprint("hello", "md5")) == 32

    def test_same_input_same_digest(self):
        assert compute_fingerprint("abc") == compute_fingerprint("abc")

    def test_different_input_different_digest(self):
        assert compute_fingerprint("abc") != compute_fingerprint("xyz")


# ---------------------------------------------------------------------------
# TestFingerprintPersistence
# ---------------------------------------------------------------------------

class TestFingerprintPersistence:
    def test_load_returns_none_when_missing(self, tmp_path):
        cfg = _cfg(tmp_path)
        assert load_fingerprint(cfg, "myjob") is None

    def test_save_and_load_roundtrip(self, tmp_path):
        cfg = _cfg(tmp_path)
        fp = Fingerprint(job_id="myjob", digest="abc123", algorithm="sha256")
        save_fingerprint(cfg, fp)
        loaded = load_fingerprint(cfg, "myjob")
        assert loaded is not None
        assert loaded.digest == "abc123"
        assert loaded.job_id == "myjob"

    def test_output_changed_true_when_no_previous(self, tmp_path):
        cfg = _cfg(tmp_path)
        assert output_changed(cfg, "job1", "some output") is True

    def test_output_changed_false_when_same(self, tmp_path):
        cfg = _cfg(tmp_path)
        fingerprint_summary(cfg, "job1", "same output")
        assert output_changed(cfg, "job1", "same output") is False

    def test_output_changed_true_when_different(self, tmp_path):
        cfg = _cfg(tmp_path)
        fingerprint_summary(cfg, "job1", "old output")
        assert output_changed(cfg, "job1", "new output") is True

    def test_disabled_always_returns_true(self, tmp_path):
        cfg = FingerprintConfig(enabled=False, state_dir=str(tmp_path))
        fingerprint_summary(cfg, "job1", "output")
        assert output_changed(cfg, "job1", "output") is True


# ---------------------------------------------------------------------------
# TestFingerprintIntegration
# ---------------------------------------------------------------------------

class TestFingerprintIntegration:
    def test_check_output_changed_combines_stdout_stderr(self, tmp_path):
        cfg = _cfg(tmp_path)
        r = _result(stdout="hello", stderr="world")
        assert check_output_changed(cfg, "j", r) is True

    def test_record_fingerprint_returns_summary_keys(self, tmp_path):
        cfg = _cfg(tmp_path)
        summary = record_fingerprint(cfg, "j", _result(stdout="out"))
        assert {"job_id", "algorithm", "digest", "changed", "previous_digest"} <= summary.keys()

    def test_fingerprint_report_changed(self, tmp_path):
        cfg = _cfg(tmp_path)
        report = fingerprint_report(cfg, "myjob", _result(stdout="data"))
        assert "CHANGED" in report
        assert "myjob" in report

    def test_fingerprint_report_unchanged(self, tmp_path):
        cfg = _cfg(tmp_path)
        r = _result(stdout="stable")
        fingerprint_report(cfg, "myjob", r)  # first run records
        report = fingerprint_report(cfg, "myjob", r)  # second run
        assert "UNCHANGED" in report

    def test_fingerprint_report_disabled(self, tmp_path):
        cfg = FingerprintConfig(enabled=False, state_dir=str(tmp_path))
        report = fingerprint_report(cfg, "myjob", _result())
        assert "disabled" in report
