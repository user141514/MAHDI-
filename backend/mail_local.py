from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name, "")
    if not value:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def public_base_url() -> str:
    return os.getenv("MAHDI_PUBLIC_BASE_URL", "http://localhost:8010").rstrip("/")


def build_reset_url(token: str) -> str:
    return f"{public_base_url()}/?reset_token={token}"


def mail_ready() -> bool:
    return bool(os.getenv("MAHDI_MAIL_HOST") and os.getenv("MAHDI_MAIL_FROM"))


def send_reset_link(to_email: str, token: str) -> bool:
    if not mail_ready():
        return False

    host = os.getenv("MAHDI_MAIL_HOST", "")
    port = int(os.getenv("MAHDI_MAIL_PORT", "587"))
    user = os.getenv("MAHDI_MAIL_USER", "")
    key = os.getenv("MAHDI_MAIL_KEY", "")
    from_email = os.getenv("MAHDI_MAIL_FROM", "")
    from_name = os.getenv("MAHDI_MAIL_FROM_NAME", "MAHDI测评系统")
    use_ssl = env_bool("MAHDI_MAIL_SSL", False)
    use_tls = env_bool("MAHDI_MAIL_TLS", not use_ssl)

    link = build_reset_url(token)
    msg = EmailMessage()
    msg["Subject"] = "MAHDI测评系统账号重置"
    msg["From"] = f"{from_name} <{from_email}>"
    msg["To"] = to_email
    msg.set_content(f"请在 1 小时内打开以下链接设置新口令：\n{link}\n\n如果这不是你的操作，请忽略本邮件。")

    client_cls = smtplib.SMTP_SSL if use_ssl else smtplib.SMTP
    with client_cls(host, port, timeout=30) as client:
        if use_tls and not use_ssl:
            client.starttls()
        if user:
            client.login(user, key)
        client.send_message(msg)
    return True
