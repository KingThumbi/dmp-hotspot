from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _make_app(monkeypatch, tmp_path, *, enabled: bool = True):
    db_path = tmp_path / "canonical_admin_redirect.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("SCHEDULER_ENABLED", "false")
    monkeypatch.setenv("ENABLE_CANONICAL_ADMIN_REDIRECT", "true" if enabled else "false")
    monkeypatch.setenv("CANONICAL_ADMIN_HOST", "www.dmpolinconnect.co.ke")
    monkeypatch.setenv("CANONICAL_ADMIN_REDIRECT_FROM_HOSTS", "dmp-hotspot.onrender.com")

    from app import create_app

    app = create_app()
    app.config.update(TESTING=True)
    return app


def test_render_host_admin_login_redirects_to_canonical_host(monkeypatch, tmp_path):
    client = _make_app(monkeypatch, tmp_path).test_client()

    response = client.get(
        "/admin/login?next=/admin-ui/transactions",
        base_url="https://dmp-hotspot.onrender.com",
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"] == (
        "https://www.dmpolinconnect.co.ke/admin/login?next=/admin-ui/transactions"
    )


def test_render_host_admin_ui_redirects_to_canonical_host(monkeypatch, tmp_path):
    client = _make_app(monkeypatch, tmp_path).test_client()

    response = client.get(
        "/admin-ui/transactions",
        base_url="https://dmp-hotspot.onrender.com",
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "https://www.dmpolinconnect.co.ke/admin-ui/transactions"


def test_render_host_api_admin_does_not_redirect(monkeypatch, tmp_path):
    client = _make_app(monkeypatch, tmp_path).test_client()

    response = client.get(
        "/api/admin/auth/me",
        base_url="https://dmp-hotspot.onrender.com",
        follow_redirects=False,
    )

    assert response.status_code == 401
    assert "Location" not in response.headers


def test_render_host_health_does_not_redirect(monkeypatch, tmp_path):
    client = _make_app(monkeypatch, tmp_path).test_client()

    response = client.get(
        "/health",
        base_url="https://dmp-hotspot.onrender.com",
        follow_redirects=False,
    )

    assert response.status_code == 200
    assert "Location" not in response.headers


def test_canonical_host_admin_routes_do_not_redirect(monkeypatch, tmp_path):
    client = _make_app(monkeypatch, tmp_path).test_client()

    response = client.get(
        "/admin/login?next=/admin-ui/transactions",
        base_url="https://www.dmpolinconnect.co.ke",
        follow_redirects=False,
    )

    assert response.status_code == 200
    assert "Location" not in response.headers


def test_canonical_admin_redirect_is_disabled_by_default(monkeypatch, tmp_path):
    client = _make_app(monkeypatch, tmp_path, enabled=False).test_client()

    response = client.get(
        "/admin/login?next=/admin-ui/transactions",
        base_url="https://dmp-hotspot.onrender.com",
        follow_redirects=False,
    )

    assert response.status_code == 200
    assert "Location" not in response.headers
