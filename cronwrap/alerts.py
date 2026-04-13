"""Alert system for cronwrap — sends notifications on job failure."""

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dataclasses import dataclass, field
from typing import Optional

from cronwrap.runner import RunResult


@dataclass
class AlertConfig:
    """Configuration for failure alerts."""
    smtp_host: str = "localhost"
    smtp_port: int = 25
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    from_addr: str = "cronwrap@localhost"
    to_addrs: list = field(default_factory=list)
    use_tls: bool = False

    @classmethod
    def from_env(cls) -> "AlertConfig":
        """Build config from environment variables."""
        to_raw = os.environ.get("CRONWRAP_ALERT_TO", "")
        to_addrs = [a.strip() for a in to_raw.split(",") if a.strip()]
        return cls(
            smtp_host=os.environ.get("CRONWRAP_SMTP_HOST", "localhost"),
            smtp_port=int(os.environ.get("CRONWRAP_SMTP_PORT", "25")),
            smtp_user=os.environ.get("CRONWRAP_SMTP_USER"),
            smtp_password=os.environ.get("CRONWRAP_SMTP_PASSWORD"),
            from_addr=os.environ.get("CRONWRAP_ALERT_FROM", "cronwrap@localhost"),
            to_addrs=to_addrs,
            use_tls=os.environ.get("CRONWRAP_SMTP_TLS", "").lower() in ("1", "true", "yes"),
        )


def build_alert_email(result: RunResult, config: AlertConfig) -> MIMEMultipart:
    """Construct the failure alert email from a RunResult."""
    msg = MIMEMultipart()
    msg["From"] = config.from_addr
    msg["To"] = ", ".join(config.to_addrs)
    msg["Subject"] = f"[cronwrap] Job failed: {result.command}"

    body = (
        f"A cron job managed by cronwrap has failed.\n\n"
        f"Command   : {result.command}\n"
        f"Exit code : {result.returncode}\n"
        f"Duration  : {result.duration:.2f}s\n\n"
        f"--- STDOUT ---\n{result.stdout or '(empty)'}\n\n"
        f"--- STDERR ---\n{result.stderr or '(empty)'}\n"
    )
    msg.attach(MIMEText(body, "plain"))
    return msg


def _connect_smtp(config: AlertConfig) -> smtplib.SMTP:
    """Create and return an SMTP connection based on the given config."""
    if config.use_tls:
        return smtplib.SMTP_SSL(config.smtp_host, config.smtp_port)
    return smtplib.SMTP(config.smtp_host, config.smtp_port)


def send_alert(result: RunResult, config: AlertConfig) -> bool:
    """Send a failure alert email. Returns True on success, False on error."""
    if not config.to_addrs:
        return False
    if result.success:
        return False

    msg = build_alert_email(result, config)
    try:
        with _connect_smtp(config) as server:
            if config.smtp_user and config.smtp_password:
                server.login(config.smtp_user, config.smtp_password)
            server.sendmail(config.from_addr, config.to_addrs, msg.as_string())
        return True
    except smtplib.SMTPException:
        return False
