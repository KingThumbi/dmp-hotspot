# app/router_agent.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from routeros_api import RouterOsApiPool
from routeros_api.exceptions import RouterOsApiCommunicationError


@dataclass
class RouterResult:
    ok: bool
    skipped: bool = False
    message: str = ""
    meta: dict[str, Any] | None = None


def _is_enabled(app) -> bool:
    return bool(app.config.get("ROUTER_AGENT_ENABLED", False))


def _pppoe_pool(app) -> RouterOsApiPool:
    host = app.config["MIKROTIK_PPPOE_HOST"]
    port = int(app.config.get("MIKROTIK_PPPOE_PORT", 8728))
    user = app.config["MIKROTIK_PPPOE_USER"]
    password = app.config["MIKROTIK_PPPOE_PASS"]

    return RouterOsApiPool(
        host,
        username=user,
        password=password,
        port=port,
        plaintext_login=True,
    )


# =========================================================
# PPPoE: Secrets + Active sessions
# =========================================================
def pppoe_secret_get(api, username: str) -> dict[str, Any] | None:
    secrets = api.get_resource("/ppp/secret")
    rows = secrets.get(name=username)
    return rows[0] if rows else None


def pppoe_secret_ensure(
    app,
    username: str,
    password: str | None,
    profile: str,
    comment: str | None = None,
) -> RouterResult:
    """
    Ensure PPPoE secret exists and has correct profile/password/comment.
    - If password is None/empty: we do NOT modify password (safer).
    """
    if not _is_enabled(app):
        return RouterResult(ok=False, skipped=True, message="Router agent disabled (ROUTER_AGENT_ENABLED=false)")

    pool = _pppoe_pool(app)
    try:
        api = pool.get_api()
        secrets = api.get_resource("/ppp/secret")

        row = pppoe_secret_get(api, username)
        if not row:
            payload: dict[str, Any] = {
                "name": username,
                "service": "pppoe",
                "profile": profile,
            }
            if password:
                payload["password"] = password
            if comment:
                payload["comment"] = comment

            secrets.add(**payload)
            return RouterResult(ok=True, message="PPPoE secret created", meta={"username": username, "profile": profile})

        secret_id = row[".id"]
        updates: dict[str, Any] = {}

        if row.get("profile") != profile:
            updates["profile"] = profile

        # Only change password if explicitly provided
        if password:
            updates["password"] = password

        # If comment is provided (even empty string), set it
        if comment is not None and row.get("comment") != comment:
            updates["comment"] = comment

        if updates:
            secrets.set(id=secret_id, **updates)
            return RouterResult(ok=True, message="PPPoE secret updated", meta={"username": username, "updates": updates})

        return RouterResult(ok=True, message="PPPoE secret already correct", meta={"username": username})

    except RouterOsApiCommunicationError as e:
        return RouterResult(ok=False, message=f"RouterOS API error: {e}", meta={"username": username})
    except Exception as e:
        return RouterResult(ok=False, message=f"Router error: {e}", meta={"username": username})
    finally:
        try:
            pool.disconnect()
        except Exception:
            pass


def pppoe_set_disabled(app, username: str, disabled: bool) -> RouterResult:
    """
    Enable/disable PPPoE secret.
    """
    if not _is_enabled(app):
        return RouterResult(ok=False, skipped=True, message="Router agent disabled (ROUTER_AGENT_ENABLED=false)")

    pool = _pppoe_pool(app)
    try:
        api = pool.get_api()
        secrets = api.get_resource("/ppp/secret")

        row = pppoe_secret_get(api, username)
        if not row:
            return RouterResult(ok=False, message="PPPoE secret not found", meta={"username": username})

        secret_id = row[".id"]
        current_disabled = (row.get("disabled") == "true")
        if current_disabled == disabled:
            return RouterResult(ok=True, message="No change", meta={"username": username, "disabled": disabled})

        secrets.set(id=secret_id, disabled=("yes" if disabled else "no"))
        return RouterResult(ok=True, message="PPPoE secret state changed", meta={"username": username, "disabled": disabled})

    except RouterOsApiCommunicationError as e:
        return RouterResult(ok=False, message=f"RouterOS API error: {e}", meta={"username": username})
    except Exception as e:
        return RouterResult(ok=False, message=f"Router error: {e}", meta={"username": username})
    finally:
        try:
            pool.disconnect()
        except Exception:
            pass


def pppoe_kick_active_sessions(app, username: str) -> RouterResult:
    """
    Disconnect active PPPoE sessions for a user.
    Useful after disabling so the user drops immediately.
    """
    if not _is_enabled(app):
        return RouterResult(ok=False, skipped=True, message="Router agent disabled (ROUTER_AGENT_ENABLED=false)")

    pool = _pppoe_pool(app)
    try:
        api = pool.get_api()
        active = api.get_resource("/ppp/active")
        rows = active.get(name=username)

        removed = 0
        for r in rows:
            active.remove(id=r[".id"])
            removed += 1

        return RouterResult(ok=True, message="Active sessions removed", meta={"username": username, "removed": removed})

    except RouterOsApiCommunicationError as e:
        return RouterResult(ok=False, message=f"RouterOS API error: {e}", meta={"username": username})
    except Exception as e:
        return RouterResult(ok=False, message=f"Router error: {e}", meta={"username": username})
    finally:
        try:
            pool.disconnect()
        except Exception:
            pass


# =========================================================
# Unified hook used by admin.py
# =========================================================
def agent_enable(app, username: str, profile: str, minutes: int, comment: str = "") -> dict:
    """
    Backwards-compatible function used by admin.py.

    PPPoE: DB expiry controls access. Router only needs:
    - secret exists
    - correct profile
    - enabled
    """
    res = pppoe_secret_ensure(app, username=username, password=None, profile=profile, comment=(comment or None))
    if not res.ok:
        if res.skipped:
            return {"ok": False, "skipped": True, "message": res.message}
        return {"ok": False, "message": res.message, "meta": res.meta}

    res2 = pppoe_set_disabled(app, username=username, disabled=False)
    if not res2.ok:
        if res2.skipped:
            return {"ok": False, "skipped": True, "message": res2.message, "meta": {"ensure": res.meta}}
        return {"ok": False, "message": res2.message, "meta": {"ensure": res.meta, "enable": res2.meta}}

    return {"ok": True, "message": "PPPoE enabled", "meta": {"ensure": res.meta, "enable": res2.meta}}
