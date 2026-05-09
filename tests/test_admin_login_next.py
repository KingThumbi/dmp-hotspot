from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.admin import safe_admin_next_url


def test_safe_admin_next_url_allows_local_admin_routes():
    assert safe_admin_next_url("/admin/dashboard") == "/admin/dashboard"
    assert safe_admin_next_url("/admin-ui/router-actions") == "/admin-ui/router-actions"
    assert safe_admin_next_url("/admin-ui/customers?q=D001") == "/admin-ui/customers?q=D001"


def test_safe_admin_next_url_blocks_external_or_public_routes():
    assert safe_admin_next_url("https://example.com/admin-ui") is None
    assert safe_admin_next_url("//example.com/admin-ui") is None
    assert safe_admin_next_url("/\\example.com") is None
    assert safe_admin_next_url("/packages") is None
