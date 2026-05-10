from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _make_app(monkeypatch, dist_dir: Path):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")

    import app as app_package

    monkeypatch.setattr(app_package, "_frontend_dist_dir", lambda: dist_dir)

    flask_app = app_package.create_app()
    flask_app.config.update(TESTING=True)
    return flask_app


def test_admin_ui_deep_link_serves_react_index(monkeypatch, tmp_path):
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    (dist_dir / "index.html").write_text(
        '<!doctype html><html><body><div id="root"></div></body></html>',
        encoding="utf-8",
    )

    client = _make_app(monkeypatch, dist_dir).test_client()

    response = client.get("/admin-ui/dashboard")

    assert response.status_code == 200
    assert response.content_type.startswith("text/html")
    assert b'id="root"' in response.data


def test_admin_ui_named_deep_links_serve_react_index(monkeypatch, tmp_path):
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    (dist_dir / "index.html").write_text(
        '<!doctype html><html><body><div id="root">react-admin</div></body></html>',
        encoding="utf-8",
    )

    client = _make_app(monkeypatch, dist_dir).test_client()

    for path in (
        "/admin-ui",
        "/admin-ui/dashboard",
        "/admin-ui/transactions",
        "/admin-ui/router-actions",
    ):
        response = client.get(path)

        assert response.status_code == 200
        assert response.content_type.startswith("text/html")
        assert b"react-admin" in response.data


def test_admin_ui_does_not_serve_index_for_static_file_paths(monkeypatch, tmp_path):
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    (dist_dir / "index.html").write_text("<html></html>", encoding="utf-8")

    client = _make_app(monkeypatch, dist_dir).test_client()

    response = client.get("/admin-ui/assets/missing.js")

    assert response.status_code == 404


def test_built_react_assets_are_served_when_present(monkeypatch, tmp_path):
    dist_dir = tmp_path / "dist"
    assets_dir = dist_dir / "assets"
    assets_dir.mkdir(parents=True)
    (dist_dir / "index.html").write_text("<html></html>", encoding="utf-8")
    (dist_dir / "logo.png").write_bytes(b"fake-png")
    (assets_dir / "index.js").write_text("console.log('ok');", encoding="utf-8")

    client = _make_app(monkeypatch, dist_dir).test_client()

    js_response = client.get("/assets/index.js")
    logo_response = client.get("/logo.png")

    assert js_response.status_code == 200
    assert b"console.log('ok')" in js_response.data
    assert logo_response.status_code == 200
    assert logo_response.data == b"fake-png"


def test_admin_ui_missing_build_returns_404(monkeypatch, tmp_path):
    client = _make_app(monkeypatch, tmp_path / "missing-dist").test_client()

    response = client.get("/admin-ui/customers")

    assert response.status_code == 404


def test_existing_flask_admin_and_api_routes_are_not_intercepted(monkeypatch, tmp_path):
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    (dist_dir / "index.html").write_text("<html>react-admin</html>", encoding="utf-8")

    client = _make_app(monkeypatch, dist_dir).test_client()

    admin_response = client.get("/admin/dashboard")
    api_response = client.get("/api/admin/auth/me")

    assert admin_response.status_code in {302, 401, 403}
    assert api_response.status_code == 401
    assert b"react-admin" not in admin_response.data
    assert b"react-admin" not in api_response.data
