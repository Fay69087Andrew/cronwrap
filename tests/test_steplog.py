import pytest
from cronwrap.steplog import Step, StepLog


def _log() -> StepLog:
    return StepLog(job_name="backup")


class TestStep:
    def test_succeeded_true_on_ok(self):
        s = Step(name="fetch", status="ok", duration_s=1.0)
        assert s.succeeded() is True

    def test_succeeded_false_on_fail(self):
        s = Step(name="fetch", status="fail", duration_s=0.5)
        assert s.succeeded() is False

    def test_to_dict_keys(self):
        s = Step(name="upload", status="skip", duration_s=0.0, message="skipped")
        d = s.to_dict()
        assert set(d) == {"name", "status", "duration_s", "message"}
        assert d["name"] == "upload"
        assert d["status"] == "skip"


class TestStepLog:
    def test_record_adds_step(self):
        log = _log()
        log.record("init", "ok", 0.1)
        assert len(log.steps) == 1
        assert log.steps[0].name == "init"

    def test_record_strips_name(self):
        log = _log()
        step = log.record("  init  ", "ok", 0.1)
        assert step.name == "init"

    def test_record_invalid_status_raises(self):
        log = _log()
        with pytest.raises(ValueError, match="Invalid status"):
            log.record("step", "unknown", 1.0)

    def test_record_empty_name_raises(self):
        log = _log()
        with pytest.raises(ValueError, match="empty"):
            log.record("", "ok", 0.5)

    def test_record_whitespace_name_raises(self):
        log = _log()
        with pytest.raises(ValueError, match="empty"):
            log.record("   ", "ok", 0.5)

    def test_failed_steps_filters_correctly(self):
        log = _log()
        log.record("a", "ok", 1.0)
        log.record("b", "fail", 0.5, "oops")
        log.record("c", "skip", 0.0)
        failed = log.failed_steps()
        assert len(failed) == 1
        assert failed[0].name == "b"

    def test_any_failed_true_when_failure_present(self):
        log = _log()
        log.record("x", "fail", 0.2)
        assert log.any_failed() is True

    def test_any_failed_false_when_all_ok(self):
        log = _log()
        log.record("x", "ok", 0.2)
        assert log.any_failed() is False

    def test_total_duration_sums_steps(self):
        log = _log()
        log.record("a", "ok", 1.5)
        log.record("b", "ok", 2.5)
        assert log.total_duration() == pytest.approx(4.0)

    def test_summary_contains_job_name(self):
        log = _log()
        log.record("a", "ok", 1.0)
        assert "backup" in log.summary()

    def test_summary_counts(self):
        log = _log()
        log.record("a", "ok", 1.0)
        log.record("b", "fail", 0.5)
        log.record("c", "skip", 0.0)
        s = log.summary()
        assert "ok=1" in s
        assert "fail=1" in s
        assert "skip=1" in s

    def test_to_dict_structure(self):
        log = _log()
        log.record("init", "ok", 0.3)
        d = log.to_dict()
        assert d["job_name"] == "backup"
        assert len(d["steps"]) == 1
        assert "any_failed" in d
        assert "total_duration_s" in d
