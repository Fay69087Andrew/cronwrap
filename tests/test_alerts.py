"""Tests for cronwrap.alerts."""

import unittest
from unittest.mock import patch, MagicMock

from cronwrap.runner import RunResult
from cronwrap.alerts import AlertConfig, build_alert_email, send_alert


def _make_result(returncode=1, stdout="out", stderr="err", duration=1.5):
    return RunResult(
        command="echo hello",
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
        duration=duration,
    )


class TestAlertConfig(unittest.TestCase):
    def test_defaults(self):
        cfg = AlertConfig()
        self.assertEqual(cfg.smtp_host, "localhost")
        self.assertEqual(cfg.smtp_port, 25)
        self.assertFalse(cfg.use_tls)
        self.assertEqual(cfg.to_addrs, [])

    def test_from_env(self):
        env = {
            "CRONWRAP_SMTP_HOST": "mail.example.com",
            "CRONWRAP_SMTP_PORT": "587",
            "CRONWRAP_ALERT_TO": "ops@example.com, dev@example.com",
            "CRONWRAP_ALERT_FROM": "cron@example.com",
            "CRONWRAP_SMTP_TLS": "true",
        }
        with patch.dict("os.environ", env, clear=False):
            cfg = AlertConfig.from_env()
        self.assertEqual(cfg.smtp_host, "mail.example.com")
        self.assertEqual(cfg.smtp_port, 587)
        self.assertEqual(cfg.to_addrs, ["ops@example.com", "dev@example.com"])
        self.assertEqual(cfg.from_addr, "cron@example.com")
        self.assertTrue(cfg.use_tls)


class TestBuildAlertEmail(unittest.TestCase):
    def test_subject_contains_command(self):
        result = _make_result()
        cfg = AlertConfig(to_addrs=["ops@example.com"])
        msg = build_alert_email(result, cfg)
        self.assertIn("echo hello", msg["Subject"])

    def test_body_contains_exit_code(self):
        result = _make_result(returncode=2)
        cfg = AlertConfig(to_addrs=["ops@example.com"])
        msg = build_alert_email(result, cfg)
        payload = msg.get_payload(0).get_payload()
        self.assertIn("2", payload)

    def test_body_contains_stdout_and_stderr(self):
        result = _make_result(stdout="hello stdout", stderr="hello stderr")
        cfg = AlertConfig(to_addrs=["ops@example.com"])
        msg = build_alert_email(result, cfg)
        payload = msg.get_payload(0).get_payload()
        self.assertIn("hello stdout", payload)
        self.assertIn("hello stderr", payload)


class TestSendAlert(unittest.TestCase):
    def test_no_recipients_returns_false(self):
        result = _make_result(returncode=1)
        cfg = AlertConfig(to_addrs=[])
        self.assertFalse(send_alert(result, cfg))

    def test_successful_job_skips_alert(self):
        result = _make_result(returncode=0)
        cfg = AlertConfig(to_addrs=["ops@example.com"])
        self.assertFalse(send_alert(result, cfg))

    @patch("cronwrap.alerts.smtplib.SMTP")
    def test_sends_email_on_failure(self, mock_smtp_cls):
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = lambda s: mock_server
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        result = _make_result(returncode=1)
        cfg = AlertConfig(to_addrs=["ops@example.com"], from_addr="cron@localhost")
        sent = send_alert(result, cfg)
        self.assertTrue(sent)

    @patch("cronwrap.alerts.smtplib.SMTP", side_effect=Exception("connection refused"))
    def test_smtp_error_returns_false(self, _mock):
        result = _make_result(returncode=1)
        cfg = AlertConfig(to_addrs=["ops@example.com"])
        self.assertFalse(send_alert(result, cfg))
