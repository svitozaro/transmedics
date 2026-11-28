"""Sending email. Kept in one place so the provider is easy to swap.

EMAIL_BACKEND=outbox (default): nothing leaves the computer. Messages are
saved and shown on the admin "Outbox" page, so you can see what pilots would get.
EMAIL_BACKEND=smtp: sends through the SMTP server in the SMTP_* settings
(Microsoft 365, Gmail, SendGrid and most providers support SMTP).
"""
import smtplib
from email.message import EmailMessage as MimeMessage

from flask import current_app

from .models import EmailMessage, db


BRAND = "TransMedics Aviation"
SIGNATURE = f"\n\n--\n{BRAND}\nPilot Vacation Portal\nThis is an automated message."


def send(to: str, subject: str, body: str):
    """Every email gets the TransMedics Aviation subject prefix and signature."""
    subject = f"{BRAND}: {subject}"
    body = body.rstrip() + SIGNATURE
    msg = EmailMessage(to=to, subject=subject, body=body, status="outbox")
    db.session.add(msg)
    cfg = current_app.config
    if cfg["EMAIL_BACKEND"] == "smtp":
        mime = MimeMessage()
        mime["From"], mime["To"], mime["Subject"] = cfg["EMAIL_FROM"], to, subject
        mime.set_content(body)
        try:
            with smtplib.SMTP(cfg["SMTP_HOST"], cfg["SMTP_PORT"], timeout=20) as s:
                s.starttls()
                if cfg["SMTP_USER"]:
                    s.login(cfg["SMTP_USER"], cfg["SMTP_PASSWORD"])
                s.send_message(mime)
            msg.status = "sent"
        except Exception as e:  # keep going, the admin sees the failure
            msg.status = f"failed: {e}"[:20]
    return msg
