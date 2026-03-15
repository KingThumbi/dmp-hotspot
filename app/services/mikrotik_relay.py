# app/services/mikrotik_relay.py
from __future__ import annotations

import os
from typing import Any

import requests


DEFAULT_TIMEOUT = 15


class RelayError(Exception):
    """Raised when the MikroTik relay request fails."""
    pass


def _get_base_url() -> str:
    base_url = (os.getenv("MIKROTIK_RELAY_URL") or "").strip().rstrip("/")
    if not base_url:
        raise RelayError("MIKROTIK_RELAY_URL is not set")
    return base_url


def _get_token() -> str:
    token = (os.getenv("MIKROTIK_RELAY_TOKEN") or "").strip()
    if not token:
        raise RelayError("MIKROTIK_RELAY_TOKEN is not set")
    return token


def _get_timeout() -> int:
    raw = (os.getenv("MIKROTIK_RELAY_TIMEOUT") or str(DEFAULT_TIMEOUT)).strip()
    try:
        timeout = int(raw)
    except ValueError as e:
        raise RelayError(f"Invalid MIKROTIK_RELAY_TIMEOUT value: {raw!r}") from e

    if timeout <= 0:
        raise RelayError("MIKROTIK_RELAY_TIMEOUT must be greater than 0")

    return timeout


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_get_token()}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _clean_username(username: str) -> str:
    value = (username or "").strip()
    if not value:
        raise RelayError("PPPoE username is required")
    return value


def _parse_response(resp: requests.Response) -> dict[str, Any]:
    try:
        data = resp.json()
        if isinstance(data, dict):
            return data
        return {"ok": False, "error": "Relay returned non-object JSON", "raw": data}
    except ValueError:
        text = (resp.text or "").strip()
        return {
            "ok": False,
            "error": "Relay returned non-JSON response",
            "raw": text[:1000],
        }


def _post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    url = f"{_get_base_url()}{path}"

    try:
        resp = requests.post(
            url,
            json=payload,
            headers=_headers(),
            timeout=_get_timeout(),
        )
    except requests.Timeout as e:
        raise RelayError(f"Relay request timed out calling {path}") from e
    except requests.ConnectionError as e:
        raise RelayError(f"Could not connect to relay at {url}") from e
    except requests.RequestException as e:
        raise RelayError(f"Relay request failed for {path}: {e}") from e

    data = _parse_response(resp)

    if not resp.ok:
        error = data.get("error") or data.get("message") or resp.text
        raise RelayError(f"Relay HTTP {resp.status_code} on {path}: {error}")

    if not data.get("ok", False):
        error = data.get("error") or data.get("message") or data
        raise RelayError(f"Relay application error on {path}: {error}")

    return data


def disable_pppoe(username: str, disconnect: bool = True) -> dict[str, Any]:
    return _post(
        "/pppoe/disable",
        {
            "username": _clean_username(username),
            "disconnect": bool(disconnect),
        },
    )


def enable_pppoe(username: str, disconnect: bool = False) -> dict[str, Any]:
    return _post(
        "/pppoe/enable",
        {
            "username": _clean_username(username),
            "disconnect": bool(disconnect),
        },
    )


def disconnect_pppoe(username: str) -> dict[str, Any]:
    return _post(
        "/pppoe/disconnect",
        {
            "username": _clean_username(username),
        },
    )
