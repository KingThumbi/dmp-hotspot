from __future__ import annotations

from datetime import datetime

from app.extensions import db
from app.models import Subscription
from app.services.mikrotik_relay import disable_pppoe, enable_pppoe


def utc_now_naive():
    # Project stores UTC naive datetimes
    return datetime.utcnow()


def get_pppoe_username(sub: Subscription) -> str | None:
    return (getattr(sub, "pppoe_username", None) or "").strip() or None


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
        username = get_pppoe_username(sub)

        relay_result = None
        relay_ok = False

        if username:
            try:
                relay_result = disable_pppoe(username, disconnect=True)
                relay_ok = True
            except Exception as e:
                errors.append(
                    {
                        "subscription_id": sub.id,
                        "username": username,
                        "error": str(e),
                    }
                )

        if relay_ok:
            sub.status = "expired"

        processed.append(
            {
                "subscription_id": sub.id,
                "username": username,
                "relay": relay_result,
            }
        )

    db.session.commit()

    return {
        "ok": True,
        "count": len(processed),
        "processed": processed,
        "errors": errors,
    }


def reactivate_subscription_after_payment(sub: Subscription) -> dict:
    username = get_pppoe_username(sub)
    if not username:
        return {"ok": False, "error": "No PPPoE username found"}

    relay_result = enable_pppoe(username, disconnect=False)

    sub.status = "active"
    db.session.commit()

    return {"ok": True, "relay": relay_result}
