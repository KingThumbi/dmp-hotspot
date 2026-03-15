from __future__ import annotations

from datetime import datetime

from app.extensions import db
from app.models import Subscription
from app.services.router_actions import disconnect_subscription, reconnect_subscription


def utc_now_naive():
    return datetime.utcnow()


def sweep_expired_accounts() -> dict:
    now = utc_now_naive()

    expired_subs = (
        Subscription.query.filter(
            Subscription.service_type == "pppoe",
            Subscription.status == "active",
            Subscription.expires_at.isnot(None),
            Subscription.expires_at < now,
            Subscription.pppoe_username.isnot(None),
        )
        .order_by(Subscription.id.asc())
        .all()
    )

    processed = []
    errors = []

    for sub in expired_subs:
        username = (sub.pppoe_username or "").strip() or None

        try:
            sub.status = "expired"
            db.session.add(sub)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            errors.append(
                {
                    "subscription_id": sub.id,
                    "username": username,
                    "error": f"db_commit_failed: {e}",
                }
            )
            continue

        try:
            action_result = disconnect_subscription(
                sub,
                reason="expired",
                dry_run=False,
            )

            processed.append(
                {
                    "subscription_id": sub.id,
                    "username": username,
                    "result": action_result,
                }
            )

        except Exception as e:
            errors.append(
                {
                    "subscription_id": sub.id,
                    "username": username,
                    "error": str(e),
                }
            )

    return {
        "ok": len(errors) == 0,
        "count": len(processed),
        "processed": processed,
        "errors": errors,
    }


def reactivate_subscription_after_payment(sub: Subscription) -> dict:
    result = reconnect_subscription(
        sub,
        reason="payment_received",
        dry_run=False,
    )
    return {"ok": bool(result.get("ok", False)), "result": result}