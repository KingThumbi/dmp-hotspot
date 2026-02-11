# app/services/mikrotik_hotspot.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from routeros_api import RouterOsApiPool


@dataclass
class HotspotResult:
    ok: bool
    message: str
    meta: dict[str, Any] | None = None
    skipped: bool = False


# ---------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------
def _cfg(app, key: str, default: Any = None) -> Any:
    return app.config.get(key, default)


def _get_hotspot_conn_params(app) -> tuple[str, int, str, str, bool, bool]:
    """
    Resolve RouterOS API connection parameters for hotspot.

    Preferred config keys (from app/config.py):
      - MIKROTIK_HOST / MIKROTIK_PORT / MIKROTIK_USER / MIKROTIK_PASSWORD / MIKROTIK_TLS

    Backward compatible fallbacks:
      - MIKROTIK_HOTSPOT_HOST / MIKROTIK_HOTSPOT_PORT / MIKROTIK_HOTSPOT_USER / MIKROTIK_HOTSPOT_PASS / MIKROTIK_HOTSPOT_TLS
      - MIKROTIK_API_PORT
      - MIKROTIK_PASS
    """
    host = _cfg(app, "MIKROTIK_HOST") or _cfg(app, "MIKROTIK_HOTSPOT_HOST")
    user = _cfg(app, "MIKROTIK_USER") or _cfg(app, "MIKROTIK_HOTSPOT_USER")
    password = (
        _cfg(app, "MIKROTIK_PASSWORD")
        or _cfg(app, "MIKROTIK_HOTSPOT_PASS")
        or _cfg(app, "MIKROTIK_PASS")
    )

    # Port keys used historically:
    # - MIKROTIK_PORT (recommended)
    # - MIKROTIK_HOTSPOT_PORT (hotspot-specific)
    # - MIKROTIK_API_PORT (older)
    port_raw = _cfg(app, "MIKROTIK_PORT") or _cfg(app, "MIKROTIK_HOTSPOT_PORT") or _cfg(app, "MIKROTIK_API_PORT") or 8728
    try:
        port = int(port_raw)
    except Exception:
        port = 8728

    tls = bool(_cfg(app, "MIKROTIK_TLS") or _cfg(app, "MIKROTIK_HOTSPOT_TLS") or False)

    # RouterOS API login mode: many setups require plaintext_login=True
    plaintext_login = bool(_cfg(app, "MIKROTIK_PLAINTEXT_LOGIN", True))

    # Safety: allow disabling router touch even if code is called
    router_enabled = bool(_cfg(app, "ROUTER_AGENT_ENABLED", False))

    if not router_enabled:
        # Still return resolved params; callers can treat router disabled as "skipped"
        return host or "", port, user or "", password or "", tls, plaintext_login

    missing = []
    if not host:
        missing.append("MIKROTIK_HOST (or MIKROTIK_HOTSPOT_HOST)")
    if not user:
        missing.append("MIKROTIK_USER (or MIKROTIK_HOTSPOT_USER)")
    if not password:
        missing.append("MIKROTIK_PASSWORD (or MIKROTIK_HOTSPOT_PASS / MIKROTIK_PASS)")

    if missing:
        raise RuntimeError("Hotspot router config missing: " + ", ".join(missing))

    return host, port, user, password, tls, plaintext_login


def _conn(app) -> RouterOsApiPool:
    """
    Create a RouterOS API connection pool using app config.

    Uses the resolved (and backward compatible) keys:
      - MIKROTIK_HOST / MIKROTIK_USER / MIKROTIK_PASSWORD / MIKROTIK_PORT
    """
    host, port, user, password, _tls, plaintext_login = _get_hotspot_conn_params(app)

    # Note: routeros_api supports TLS via port 8729 typically, but setups vary.
    # We keep the pool creation simple; if you use TLS, set port accordingly.
    return RouterOsApiPool(
        host=host,
        username=user,
        password=password,
        port=port,
        plaintext_login=plaintext_login,
    )


# ---------------------------------------------------------------------
# Small utilities
# ---------------------------------------------------------------------
def _iso(dt: Optional[datetime]) -> str:
    return dt.isoformat() if isinstance(dt, datetime) else ""


def _build_comment(*parts: str) -> str:
    cleaned = [p.strip() for p in parts if p and p.strip()]
    comment = " ".join(cleaned)
    return comment[:240]


def _normalize_row(result: Any) -> Optional[dict[str, Any]]:
    """
    routeros_api .get(...) may return:
      - list[dict]
      - dict
      - [] / None
    Normalize to a single dict row or None.
    """
    if isinstance(result, list):
        return result[0] if result else None
    if isinstance(result, dict):
        return result if result else None
    return None


def _router_disabled(app) -> bool:
    return not bool(_cfg(app, "ROUTER_AGENT_ENABLED", False))


# ---------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------
def ensure_hotspot_user(
    app,
    username: str,
    profile: str,
    expires_at: datetime,
    *,
    password: str = "",
    comment_extra: str = "",
) -> HotspotResult:
    """
    Create or update /ip/hotspot/user with:
      - profile = package.mikrotik_profile
      - disabled = no
      - comment including expiry timestamp (UTC-naive string)

    NOTE:
    - max_devices is enforced by RouterOS hotspot USER PROFILE via shared-users.
    """
    username = (username or "").strip()
    profile = (profile or "").strip()

    if not username:
        return HotspotResult(ok=False, message="Missing username")
    if not profile:
        return HotspotResult(ok=False, message="Missing profile")

    if _router_disabled(app):
        return HotspotResult(
            ok=True,
            skipped=True,
            message="Router automation disabled (ROUTER_AGENT_ENABLED=false); skipped ensure_hotspot_user",
            meta={"username": username, "profile": profile, "expires_at": _iso(expires_at)},
        )

    pool = _conn(app)
    try:
        api = pool.get_api()
        users = api.get_resource("/ip/hotspot/user")

        comment = _build_comment(
            f"exp={_iso(expires_at)}",
            f"pkg={profile}",
            comment_extra,
        )

        row = _normalize_row(users.get(name=username))

        if row and row.get(".id"):
            users.set(
                id=row[".id"],
                profile=profile,
                disabled="no",
                comment=comment,
            )
            return HotspotResult(
                ok=True,
                message="Hotspot user updated/enabled",
                meta={"username": username, "profile": profile},
            )

        # Password can be blank (voucher style)
        users.add(
            name=username,
            password=password,
            profile=profile,
            disabled="no",
            comment=comment,
        )
        return HotspotResult(
            ok=True,
            message="Hotspot user created/enabled",
            meta={"username": username, "profile": profile},
        )

    except Exception as e:
        return HotspotResult(
            ok=False,
            message=f"ensure_hotspot_user failed: {e}",
            meta={"username": username, "profile": profile},
        )
    finally:
        try:
            pool.disconnect()
        except Exception:
            pass


def disable_hotspot_user(app, username: str, *, reason: str = "expired") -> HotspotResult:
    """
    Disable /ip/hotspot/user for the given username.
    Does NOT delete the user; it just disables it.
    """
    username = (username or "").strip()
    if not username:
        return HotspotResult(ok=False, message="Missing username")

    if _router_disabled(app):
        return HotspotResult(
            ok=True,
            skipped=True,
            message="Router automation disabled (ROUTER_AGENT_ENABLED=false); skipped disable_hotspot_user",
            meta={"username": username, "reason": reason},
        )

    pool = _conn(app)
    try:
        api = pool.get_api()
        users = api.get_resource("/ip/hotspot/user")

        row = _normalize_row(users.get(name=username))
        if not row or not row.get(".id"):
            return HotspotResult(ok=True, message="User not found (nothing to disable)", meta={"username": username})

        new_comment = _build_comment(row.get("comment", ""), f"disabled={reason}")
        users.set(id=row[".id"], disabled="yes", comment=new_comment)
        return HotspotResult(ok=True, message="Hotspot user disabled", meta={"username": username})

    except Exception as e:
        return HotspotResult(ok=False, message=f"disable_hotspot_user failed: {e}", meta={"username": username})
    finally:
        try:
            pool.disconnect()
        except Exception:
            pass


def kick_hotspot_active(app, username: str) -> HotspotResult:
    """
    Disconnect active hotspot sessions for this user so policy applies immediately.
    Returns number of sessions removed.

    RouterOS path: /ip/hotspot/active
    Filter field:  user=<username>
    """
    username = (username or "").strip()
    if not username:
        return HotspotResult(ok=False, message="Missing username")

    if _router_disabled(app):
        return HotspotResult(
            ok=True,
            skipped=True,
            message="Router automation disabled (ROUTER_AGENT_ENABLED=false); skipped kick_hotspot_active",
            meta={"username": username, "removed": 0},
        )

    pool = _conn(app)
    removed = 0
    try:
        api = pool.get_api()
        active = api.get_resource("/ip/hotspot/active")

        rows = active.get(user=username)
        if isinstance(rows, dict):
            rows = [rows]
        rows = rows or []

        for r in rows:
            rid = r.get(".id")
            if rid:
                active.remove(id=rid)
                removed += 1

        return HotspotResult(ok=True, message="Hotspot active sessions removed", meta={"username": username, "removed": removed})

    except Exception as e:
        return HotspotResult(ok=False, message=f"kick_hotspot_active failed: {e}", meta={"username": username, "removed": removed})
    finally:
        try:
            pool.disconnect()
        except Exception:
            pass


def bind_user_mac(app, username: str, mac: str, *, comment_extra: str = "") -> HotspotResult:
    """
    Optional: lock a user to a specific MAC using /ip/hotspot/ip-binding.

    Notes:
    - OPTIONAL; shared-users profiles usually enough.
    - If used, best for max_devices=1 packages.
    - type=bypassed reduces repeated login friction.
    """
    username = (username or "").strip()
    mac = (mac or "").strip()

    if not username:
        return HotspotResult(ok=False, message="Missing username")
    if not mac:
        return HotspotResult(ok=False, message="Missing mac")

    if _router_disabled(app):
        return HotspotResult(
            ok=True,
            skipped=True,
            message="Router automation disabled (ROUTER_AGENT_ENABLED=false); skipped bind_user_mac",
            meta={"username": username, "mac": mac},
        )

    pool = _conn(app)
    try:
        api = pool.get_api()
        bindings = api.get_resource("/ip/hotspot/ip-binding")

        row = _normalize_row(bindings.get(mac_address=mac))
        comment = _build_comment(f"user={username}", comment_extra)

        if row and row.get(".id"):
            bindings.set(id=row[".id"], type="bypassed", comment=comment)
            return HotspotResult(ok=True, message="MAC binding updated", meta={"username": username, "mac": mac})

        bindings.add(mac_address=mac, type="bypassed", comment=comment)
        return HotspotResult(ok=True, message="MAC binding created", meta={"username": username, "mac": mac})

    except Exception as e:
        return HotspotResult(ok=False, message=f"bind_user_mac failed: {e}", meta={"username": username, "mac": mac})
    finally:
        try:
            pool.disconnect()
        except Exception:
            pass
