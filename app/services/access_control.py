from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

@dataclass(frozen=True)
class AccessResult:
    ok: bool
    message: str
    detail: Optional[str] = None


class AccessController:
    """
    Thin abstraction over router operations.
    For now you can stub these methods and wire MikroTik API later,
    without changing the rest of your billing/payment code.
    """

    def __init__(self, *, enabled: bool = True):
        self.enabled = enabled

    # -----------------------
    # HOTSPOT
    # -----------------------
    def hotspot_grant(self, *, username: str, expires_at: datetime) -> AccessResult:
        if not self.enabled:
            return AccessResult(True, "Hotspot grant skipped (router disabled).")
        # TODO: call MikroTik API to create/enable user & set limit/timeout
        return AccessResult(True, f"Hotspot granted to {username} until {expires_at.isoformat()}")

    def hotspot_revoke(self, *, username: str) -> AccessResult:
        if not self.enabled:
            return AccessResult(True, "Hotspot revoke skipped (router disabled).")
        # TODO: MikroTik API disable/remove user
        return AccessResult(True, f"Hotspot revoked for {username}")

    # -----------------------
    # PPPoE
    # -----------------------
    def pppoe_enable(self, *, username: str) -> AccessResult:
        if not self.enabled:
            return AccessResult(True, "PPPoE enable skipped (router disabled).")
        # TODO: MikroTik API enable PPP secret
        return AccessResult(True, f"PPPoE enabled for {username}")

    def pppoe_disable(self, *, username: str) -> AccessResult:
        if not self.enabled:
            return AccessResult(True, "PPPoE disable skipped (router disabled).")
        # TODO: MikroTik API disable PPP secret
        return AccessResult(True, f"PPPoE disabled for {username}")
