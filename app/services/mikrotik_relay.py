# app/services/mikrotik_relay.py
import os
import requests

RELAY_BASE_URL = (os.getenv("MIKROTIK_RELAY_URL") or "").rstrip("/")
RELAY_TOKEN = os.getenv("MIKROTIK_RELAY_TOKEN") or ""
TIMEOUT = int(os.getenv("MIKROTIK_RELAY_TIMEOUT", "15"))


class RelayError(Exception):
    pass


def _post(path: str, payload: dict) -> dict:
    if not RELAY_BASE_URL:
        raise RelayError("MIKROTIK_RELAY_URL is not set")
    if not RELAY_TOKEN:
        raise RelayError("MIKROTIK_RELAY_TOKEN is not set")

    url = f"{RELAY_BASE_URL}{path}"
    resp = requests.post(
        url,
        json=payload,
        headers={
            "Authorization": f"Bearer {RELAY_TOKEN}",
            "Content-Type": "application/json",
        },
        timeout=TIMEOUT,
    )

    try:
        data = resp.json()
    except Exception:
        data = {"ok": False, "error": resp.text}

    if not resp.ok:
        raise RelayError(f"Relay HTTP {resp.status_code}: {data}")

    if not data.get("ok", False):
        raise RelayError(f"Relay error: {data}")

    return data


def disable_pppoe(username: str, disconnect: bool = True) -> dict:
    return _post("/pppoe/disable", {
        "username": username,
        "disconnect": disconnect,
    })


def enable_pppoe(username: str, disconnect: bool = False) -> dict:
    return _post("/pppoe/enable", {
        "username": username,
        "disconnect": disconnect,
    })


def disconnect_pppoe(username: str) -> dict:
    return _post("/pppoe/disconnect", {
        "username": username,
    })
