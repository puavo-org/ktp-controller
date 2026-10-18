import fastapi.testclient
import pytest

import ktp_controller.wui.main


@pytest.fixture
def wui_client():
    return fastapi.testclient.TestClient(
        ktp_controller.wui.main.APP, follow_redirects=False
    )


def test_get_root_redirects_to_invigilator(wui_client):
    response = wui_client.get("/")

    assert response.status_code == 303
    assert response.headers["location"] == "/invigilator/"


def test_get_root_redirect_honors_forwarded_prefix(wui_client):
    # nginx forwards the full, un-stripped path alongside the header (see
    # ktp_controller.nginx.enable_nginx_wui_tls_reverse_proxy) - Starlette's
    # routing recomputes each route's relative path on the fly from
    # root_path, rather than expecting it pre-stripped.
    response = wui_client.get(
        "/remote/12345/", headers={"X-Forwarded-Prefix": "/remote/12345"}
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/remote/12345/invigilator/"


def test_get_root_redirect_ignores_malformed_forwarded_prefix(wui_client):
    response = wui_client.get("/", headers={"X-Forwarded-Prefix": "/not-remote/12345"})

    assert response.status_code == 303
    assert response.headers["location"] == "/invigilator/"


def test_static_file_served_through_forwarded_prefix(wui_client):
    # Regression test: StaticFiles is mounted (APP.mount), and a Mount
    # accumulates root_path for its child scope rather than stripping its
    # own prefix from scope["path"] - it relies on nginx forwarding the
    # full, un-stripped path (see
    # ktp_controller.nginx.enable_nginx_wui_tls_reverse_proxy) so Starlette
    # can recompute the mount-relative path on the fly. Forwarding an
    # already-stripped path here previously made every static asset 404
    # once a prefix was in play.
    response = wui_client.get(
        "/remote/12345/static/pico.min.css",
        headers={"X-Forwarded-Prefix": "/remote/12345"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/css; charset=utf-8"
