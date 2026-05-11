from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture()
def admin_role_app(monkeypatch, tmp_path):
    db_path = tmp_path / "admin_user_roles.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("SCHEDULER_ENABLED", "false")

    from app import create_app
    from app.extensions import db
    from app.models import AdminAuditLog, AdminUser

    app = create_app()
    app.config.update(TESTING=True)

    with app.app_context():
        db.drop_all()
        db.metadata.create_all(db.engine, tables=[AdminUser.__table__, AdminAuditLog.__table__])

    yield app

    with app.app_context():
        db.session.remove()
        db.drop_all()


def _create_user(email: str, role: str, password: str = "CorrectPassword123!"):
    from app.extensions import db
    from app.models import AdminUser

    user = AdminUser(email=email, is_active=True, role=role, is_superadmin=False)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user.id


def _login(client, email: str, password: str = "CorrectPassword123!"):
    return client.post(
        "/admin/login",
        data={"email": email, "password": password},
        follow_redirects=False,
    )


def test_admin_can_update_another_users_role(admin_role_app):
    from app.extensions import db
    from app.models import AdminUser

    with admin_role_app.app_context():
        _create_user("admin@example.com", "admin")
        target_id = _create_user("support@example.com", "support")

    client = admin_role_app.test_client()
    assert _login(client, "admin@example.com").status_code == 302

    response = client.post(
        f"/admin/users/{target_id}/role",
        data={"role": "finance"},
        follow_redirects=False,
    )

    assert response.status_code == 302

    with admin_role_app.app_context():
        db.session.expire_all()
        target = db.session.get(AdminUser, target_id)
        assert target.role == "finance"


def test_non_admin_cannot_update_roles(admin_role_app):
    from app.extensions import db
    from app.models import AdminUser

    with admin_role_app.app_context():
        _create_user("support@example.com", "support")
        target_id = _create_user("finance@example.com", "finance")

    client = admin_role_app.test_client()
    assert _login(client, "support@example.com").status_code == 302

    response = client.post(
        f"/admin/users/{target_id}/role",
        data={"role": "admin"},
        follow_redirects=False,
    )

    assert response.status_code == 403

    with admin_role_app.app_context():
        db.session.expire_all()
        target = db.session.get(AdminUser, target_id)
        assert target.role == "finance"


def test_invalid_role_is_rejected(admin_role_app):
    from app.extensions import db
    from app.models import AdminUser

    with admin_role_app.app_context():
        _create_user("admin@example.com", "admin")
        target_id = _create_user("ops@example.com", "ops")

    client = admin_role_app.test_client()
    assert _login(client, "admin@example.com").status_code == 302

    response = client.post(
        f"/admin/users/{target_id}/role",
        data={"role": "owner"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith(f"/admin/users/{target_id}/role")

    with admin_role_app.app_context():
        db.session.expire_all()
        target = db.session.get(AdminUser, target_id)
        assert target.role == "ops"


def test_admin_cannot_demote_self(admin_role_app):
    from app.extensions import db
    from app.models import AdminUser

    with admin_role_app.app_context():
        admin_id = _create_user("admin@example.com", "admin")

    client = admin_role_app.test_client()
    assert _login(client, "admin@example.com").status_code == 302

    response = client.post(
        f"/admin/users/{admin_id}/role",
        data={"role": "support"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/users")

    with admin_role_app.app_context():
        db.session.expire_all()
        admin = db.session.get(AdminUser, admin_id)
        assert admin.role == "admin"
