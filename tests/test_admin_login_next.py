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


def test_admin_login_form_preserves_relative_admin_ui_next(monkeypatch, tmp_path):
    db_path = tmp_path / "admin_login_next.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("SCHEDULER_ENABLED", "false")

    from app import create_app

    app = create_app()
    app.config.update(TESTING=True)
    client = app.test_client()

    response = client.get(
        "/admin/login?next=/admin-ui/transactions",
        base_url="https://dmp-hotspot.onrender.com",
    )

    assert response.status_code == 200
    assert b'action="/admin/login"' in response.data
    assert b'name="next" value="/admin-ui/transactions"' in response.data
    assert b"https://dmp-hotspot.onrender.com/admin-ui/transactions" not in response.data


def test_admin_login_success_redirects_to_relative_admin_ui_next(monkeypatch, tmp_path):
    db_path = tmp_path / "admin_login_redirect.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("SCHEDULER_ENABLED", "false")

    from app import create_app
    from app.extensions import db
    from app.models import AdminAuditLog, AdminUser

    app = create_app()
    app.config.update(TESTING=True)

    with app.app_context():
        db.metadata.create_all(db.engine, tables=[AdminUser.__table__, AdminAuditLog.__table__])
        user = AdminUser(email="admin@example.com", is_active=True, role="admin", is_superadmin=True)
        user.set_password("correct-password")
        db.session.add(user)
        db.session.commit()

    client = app.test_client()
    response = client.post(
        "/admin/login",
        data={
            "email": "admin@example.com",
            "password": "correct-password",
            "next": "/admin-ui/transactions",
        },
        base_url="https://dmp-hotspot.onrender.com",
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/admin-ui/transactions"
