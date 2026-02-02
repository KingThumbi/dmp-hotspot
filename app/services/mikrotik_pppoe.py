from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any, List

import os
from routeros_api import RouterOsApiPool


@dataclass
class PPPoEConfig:
    host: str
    user: str
    password: str
    port: int = 8728
    use_tls: bool = False


def load_pppoe_config() -> PPPoEConfig:
    host = os.getenv("MIKROTIK_PPPOE_HOST", "").strip()
    user = os.getenv("MIKROTIK_PPPOE_USER", "").strip()
    password = os.getenv("MIKROTIK_PPPOE_PASS", "").strip()
    port = int(os.getenv("MIKROTIK_PPPOE_PORT", "8728"))
    use_tls = os.getenv("MIKROTIK_PPPOE_TLS", "false").lower() == "true"

    if not host or not user or not password:
        raise RuntimeError("Missing MikroTik PPPoE env vars: MIKROTIK_PPPOE_HOST/USER/PASS")

    return PPPoEConfig(host=host, user=user, password=password, port=port, use_tls=use_tls)


class MikroTikPPPoE:
    """
    RouterOS PPPoE operations:
    - enable/disable /ppp secret
    - change /ppp secret profile
    - kick active session (/ppp active remove)
    """

    def __init__(self, cfg: Optional[PPPoEConfig] = None):
        self.cfg = cfg or load_pppoe_config()

    def _api(self):
        pool = RouterOsApiPool(
            host=self.cfg.host,
            username=self.cfg.user,
            password=self.cfg.password,
            port=self.cfg.port,
            use_ssl=self.cfg.use_tls,
            ssl_verify=self.cfg.use_tls,  # safe default
            plaintext_login=not self.cfg.use_tls,
        )
        api = pool.get_api()
        return pool, api

    # -------------------------------
    # Secrets
    # -------------------------------
    def secret_get(self, name: str) -> Optional[Dict[str, Any]]:
        pool, api = self._api()
        try:
            secrets = api.get_resource("/ppp/secret")
            rows = secrets.get()
            for r in rows:
                if r.get("name") == name:
                    return r
            return None
        finally:
            pool.disconnect()

    def secret_create(self, name: str, password: str, profile: str, comment: str = "") -> None:
        pool, api = self._api()
        try:
            secrets = api.get_resource("/ppp/secret")
            payload = {
                "name": name,
                "password": password,
                "service": "pppoe",
                "profile": profile,
            }
            if comment:
                payload["comment"] = comment
            secrets.add(**payload)
        finally:
            pool.disconnect()

    def secret_set_profile(self, name: str, profile: str) -> None:
        pool, api = self._api()
        try:
            secrets = api.get_resource("/ppp/secret")
            rows = secrets.get()
            target_id = None
            for r in rows:
                if r.get("name") == name:
                    target_id = r.get(".id")
                    break
            if not target_id:
                raise RuntimeError(f"PPPoE secret not found: {name}")
            secrets.set(id=target_id, profile=profile)
        finally:
            pool.disconnect()

    def secret_disable(self, name: str, comment: str = "unpaid") -> None:
        pool, api = self._api()
        try:
            secrets = api.get_resource("/ppp/secret")
            rows = secrets.get()
            target_id = None
            old_comment = ""
            for r in rows:
                if r.get("name") == name:
                    target_id = r.get(".id")
                    old_comment = r.get("comment", "") or ""
                    break
            if not target_id:
                raise RuntimeError(f"PPPoE secret not found: {name}")

            # preserve existing comment, but append marker
            new_comment = old_comment
            if comment and comment.lower() not in (old_comment or "").lower():
                new_comment = (old_comment + " | " + comment).strip(" |")

            secrets.set(id=target_id, disabled="yes", comment=new_comment)
        finally:
            pool.disconnect()

    def secret_enable(self, name: str, comment: str = "") -> None:
        pool, api = self._api()
        try:
            secrets = api.get_resource("/ppp/secret")
            rows = secrets.get()
            target_id = None
            for r in rows:
                if r.get("name") == name:
                    target_id = r.get(".id")
                    break
            if not target_id:
                raise RuntimeError(f"PPPoE secret not found: {name}")

            payload = {"id": target_id, "disabled": "no"}
            if comment:
                payload["comment"] = comment
            secrets.set(**payload)
        finally:
            pool.disconnect()

    # -------------------------------
    # Active session kick
    # -------------------------------
    def kick(self, name: str) -> bool:
        """
        If user is active, remove session so they reconnect.
        Returns True if session was removed.
        """
        pool, api = self._api()
        try:
            active = api.get_resource("/ppp/active")
            rows = active.get()
            for r in rows:
                if r.get("name") == name:
                    active.remove(id=r.get(".id"))
                    return True
            return False
        finally:
            pool.disconnect()
