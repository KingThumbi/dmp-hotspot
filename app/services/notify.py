from __future__ import annotations
import os
import requests
from flask import current_app

def _env(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()

def notify_admin_new_lead(payload: dict) -> None:
    """
    Best-effort notifications. Never throws to caller.
    payload keys: kind, name, phone, estate, message, id, created_at
    """
    try:
        _notify_whatsapp(payload)
    except Exception:
        current_app.logger.exception("WhatsApp notify failed")

    try:
        _notify_email(payload)
    except Exception:
        current_app.logger.exception("Email notify failed")


def _notify_whatsapp(payload: dict) -> None:
    """
    WhatsApp Cloud API (Meta).
    Env:
      WHATSAPP_ENABLED=true
      WHATSAPP_TOKEN=...
      WHATSAPP_PHONE_NUMBER_ID=...
      WHATSAPP_TO=2547xxxxxxx (admin number)
    """
    enabled = _env("WHATSAPP_ENABLED", "false").lower() in {"1","true","yes","y","on"}
    if not enabled:
        return

    token = _env("WHATSAPP_TOKEN")
    phone_number_id = _env("WHATSAPP_PHONE_NUMBER_ID")
    to = _env("WHATSAPP_TO")
    if not token or not phone_number_id or not to:
        return

    msg = (
        f"New {payload.get('kind','lead')} lead\n"
        f"Name: {payload.get('name','')}\n"
        f"Phone: {payload.get('phone','')}\n"
        f"Estate: {payload.get('estate','')}\n"
        f"Message: {payload.get('message','')}\n"
        f"ID: {payload.get('id','')}"
    )

    url = f"https://graph.facebook.com/v20.0/{phone_number_id}/messages"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": msg},
    }
    requests.post(url, headers=headers, json=data, timeout=10).raise_for_status()


def _notify_email(payload: dict) -> None:
    """
    Simple SMTP email.
    Env:
      EMAIL_ENABLED=true
      SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS
      EMAIL_TO (comma separated)
      EMAIL_FROM
    """
    enabled = _env("EMAIL_ENABLED", "false").lower() in {"1","true","yes","y","on"}
    if not enabled:
        return

    import smtplib
    from email.message import EmailMessage

    host = _env("SMTP_HOST")
    port = int(_env("SMTP_PORT", "587"))
    user = _env("SMTP_USER")
    pw = _env("SMTP_PASS")
    to_list = [x.strip() for x in _env("EMAIL_TO").split(",") if x.strip()]
    mail_from = _env("EMAIL_FROM", user)

    if not host or not to_list or not mail_from:
        return

    subject = f"[Dmpolin] New {payload.get('kind','lead').title()} Lead #{payload.get('id','')}"
    body = (
        f"New lead received:\n\n"
        f"Kind: {payload.get('kind','')}\n"
        f"Name: {payload.get('name','')}\n"
        f"Phone: {payload.get('phone','')}\n"
        f"Estate: {payload.get('estate','')}\n"
        f"Message: {payload.get('message','')}\n"
        f"Source: {payload.get('source','')}\n"
        f"Created: {payload.get('created_at','')}\n"
        f"ID: {payload.get('id','')}\n"
    )

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = mail_from
    msg["To"] = ", ".join(to_list)
    msg.set_content(body)

    with smtplib.SMTP(host, port, timeout=10) as s:
        s.starttls()
        if user and pw:
            s.login(user, pw)
        s.send_message(msg)
