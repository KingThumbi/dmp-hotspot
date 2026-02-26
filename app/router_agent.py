# app/router_agent.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from routeros_api import RouterOsApiPool
from routeros_api.exceptions import RouterOsApiCommunicationError


# =========================================================
# Result container
# =========================================================
@dataclass
class RouterResult:
    ok: bool
    skipped: bool = False
    message: str = ""
    meta: dict[str, Any] | None = None


# =========================================================
# Config helpers
# =========================================================
def _is_enabled(app) -> bool:
    return bool(app.config.get("ROUTER_AGENT_ENABLED", False))


def _pppoe_pool(app) -> Optional[RouterOsApiPool]:
    """
    Build a RouterOS API pool for PPPoE actions.

    Returns None if required config is missing. This makes the router agent
    fail-safe (skip) instead of crashing with KeyError in production.
    """
    host = (app.config.get("MIKROTIK_PPPOE_HOST") or "").strip()
    user = (app.config.get("MIKROTIK_PPPOE_USER") or "").strip()
    password = (app.config.get("MIKROTIK_PPPOE_PASS") or "").strip()
    port = int(app.config.get("MIKROTIK_PPPOE_PORT", 8728) or 8728)

    if not host or not user or not password:
        return None

    return RouterOsApiPool(
        host,
        username=user,
        password=password,
        port=port,
        plaintext_login=True,
    )


def _require_agent_and_pool(app) -> tuple[Optional[RouterOsApiPool], Optional[RouterResult]]:
    """
    Common gate:
    - Router agent must be enabled
    - PPPoE RouterOS config must be present
    """
    if not _is_enabled(app):
        return None, RouterResult(ok=False, skipped=True, message="Router agent disabled (ROUTER_AGENT_ENABLED=false)")

    pool = _pppoe_pool(app)
    if pool is None:
        return None, RouterResult(
            ok=False,
            skipped=True,
            message="Missing PPPoE router config (MIKROTIK_PPPOE_HOST/MIKROTIK_PPPOE_USER/MIKROTIK_PPPOE_PASS)",
        )

    return pool, None


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

    Safety rules:
    - If password is None/empty: do NOT change password.
    - If comment is None: do NOT change comment.
    """
    username = (username or "").strip()
    profile = (profile or "").strip()

    if not username:
        return RouterResult(ok=False, message="Missing username")
    if not profile:
        return RouterResult(ok=False, message="Missing profile")

    pool, gate = _require_agent_and_pool(app)
    if gate:
        return gate

    assert pool is not None
    try:
        api = pool.get_api()
        secrets = api.get_resource("/ppp/secret")

        row = pppoe_secret_get(api, username)
        if not row:
            payload: dict[str, Any] = {"name": username, "service": "pppoe", "profile": profile}
            if password:
                payload["password"] = password
            if comment:
                payload["comment"] = comment

            secrets.add(**payload)
            return RouterResult(ok=True, message="PPPoE secret created", meta={"username": username, "profile": profile})

        secret_id = row.get(".id")
        if not secret_id:
            return RouterResult(ok=False, message="Router returned secret without .id", meta={"username": username})

        updates: dict[str, Any] = {}

        if row.get("profile") != profile:
            updates["profile"] = profile

        # Only change password if explicitly provided
        if password:
            updates["password"] = password

        # Only change comment if explicitly provided (even empty string)
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
    Enable/disable PPPoE secret (disabled=yes/no).
    """
    username = (username or "").strip()
    if not username:
        return RouterResult(ok=False, message="Missing username")

    pool, gate = _require_agent_and_pool(app)
    if gate:
        return gate

    assert pool is not None
    try:
        api = pool.get_api()
        secrets = api.get_resource("/ppp/secret")

        row = pppoe_secret_get(api, username)
        if not row:
            return RouterResult(ok=False, message="PPPoE secret not found", meta={"username": username})

        secret_id = row.get(".id")
        if not secret_id:
            return RouterResult(ok=False, message="Router returned secret without .id", meta={"username": username})

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
    Disconnect active PPPoE sessions for a user (/ppp/active remove).
    Useful after disabling so the user drops immediately.
    """
    username = (username or "").strip()
    if not username:
        return RouterResult(ok=False, message="Missing username")

    pool, gate = _require_agent_and_pool(app)
    if gate:
        return gate

    assert pool is not None
    try:
        api = pool.get_api()
        active = api.get_resource("/ppp/active")
        rows = active.get(name=username)

        removed = 0
        for r in rows:
            rid = r.get(".id")
            if rid:
                active.remove(id=rid)
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
# Unified hook used by admin.py (backwards-compatible)
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
