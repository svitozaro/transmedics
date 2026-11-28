"""Sending email. Kept in one place so the provider is easy to swap.

EMAIL_BACKEND=outbox (default): nothing leaves the computer. Messages are
saved and shown on the admin "Outbox" page, so you can see what pilots would get.
EMAIL_BACKEND=smtp: sends through the SMTP server in the SMTP_* settings
(Microsoft 365, Gmail, SendGrid and most providers support SMTP).

Every email has a plain-text version and a branded HTML version with the
TransMedics logo. The logo is a PNG, because most email programs cannot show SVG.
"""
import html
import re
import smtplib
from email.message import EmailMessage as MimeMessage
from pathlib import Path

from flask import current_app

from .models import EmailMessage, db

BRAND = "TransMedics Aviation"
BRAND_RED = "#8b2434"  # from the official logo
SIGNATURE = f"\n\n--\n{BRAND}\nPilot Vacation Portal\nThis is an automated message."
LOGO_PNG = Path(__file__).parent / "static" / "brand" / "logo-email.png"
LOGO_CID = "tmdx-logo"


def render_html(body: str, logo_src: str) -> str:
    """Branded HTML version of a plain-text email body."""
    text = body.split("\n\n--\n")[0]  # the HTML footer replaces the text signature
    safe = html.escape(text)
    safe = re.sub(r"(https?://[^\s<]+)", r'<a href="\1" target="_blank" style="color:%s">\1</a>' % BRAND_RED, safe)
    paras = "".join(f'<p style="margin:0 0 14px">{p.replace(chr(10), "<br>")}</p>'
                    for p in safe.split("\n\n") if p.strip())
    return f"""<!doctype html><html><body style="margin:0;padding:24px;background:#f5f6f8;font-family:Arial,Helvetica,sans-serif;color:#1d2330">
<table role="presentation" width="100%" style="max-width:560px;margin:0 auto;background:#fff;border-radius:8px;border-top:5px solid {BRAND_RED}">
<tr><td style="padding:24px 28px 8px"><img src="{logo_src}" alt="TransMedics" height="64" style="display:block;height:64px;width:auto">
<div style="margin-top:10px;color:{BRAND_RED};font-weight:bold;letter-spacing:.02em">{BRAND}</div>
<div style="color:#667085;font-size:13px">Pilot Vacation Portal</div></td></tr>
<tr><td style="padding:16px 28px 8px;font-size:15px;line-height:1.5">{paras}</td></tr>
<tr><td style="padding:12px 28px 22px;border-top:1px solid #dde1e7;color:#667085;font-size:12px">{BRAND} · Pilot Vacation Portal<br>This is an automated message.</td></tr>
</table></body></html>"""


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
        mime.add_alternative(render_html(body, f"cid:{LOGO_CID}"), subtype="html")
        mime.get_payload()[1].add_related(LOGO_PNG.read_bytes(), "image", "png",
                                          cid=f"<{LOGO_CID}>")
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
