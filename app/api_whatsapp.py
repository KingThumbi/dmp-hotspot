from __future__ import annotations

import hashlib
import hmac
import json
import os

from flask import Blueprint, current_app, jsonify, request

api_whatsapp_bp = Blueprint("api_whatsapp", __name__)


def _verify_signature(raw_body: bytes, signature_header: str | None) -> bool:
    app_secret = os.getenv("WHATSAPP_APP_SECRET", "").strip()
    if not app_secret or not signature_header:
        return False

    expected = "sha256=" + hmac.new(
        app_secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, signature_header)


@api_whatsapp_bp.get("/api/whatsapp/webhook")
def whatsapp_webhook_verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN", "").strip()

    if mode == "subscribe" and token == verify_token:
        return challenge or "", 200

    return "Verification failed", 403


@api_whatsapp_bp.post("/api/whatsapp/webhook")
def whatsapp_webhook_receive():
    raw_body = request.get_data()
    signature = request.headers.get("X-Hub-Signature-256")

    # Optional but recommended if APP_SECRET is configured.
    if os.getenv("WHATSAPP_APP_SECRET"):
        if not _verify_signature(raw_body, signature):
            return jsonify({"ok": False, "error": "Invalid signature"}), 403

    payload = request.get_json(silent=True) or {}

    # For now, log and acknowledge.
    current_app.logger.info("WhatsApp webhook payload: %s", json.dumps(payload))

    return jsonify({"ok": True}), 200