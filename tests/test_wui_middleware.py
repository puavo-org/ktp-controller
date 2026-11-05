import fastapi
import fastapi.testclient
import pytest

import ktp_controller.wui.middleware as middleware
from ktp_controller import SETTINGS

# The device's own WUI origin, as nginx forwards it (see
# ktp_controller/nginx.py's `proxy_set_header Host $http_host;`).
_DEVICE_ORIGIN = "https://johdanto-rivitys.koe.abitti.net:8443"
_EXAMOMATIC_HOST = "staging-koejakaja.opinsys.fi"
_EXAMOMATIC_ORIGIN = f"https://{_EXAMOMATIC_HOST}"


def _make_app() -> fastapi.FastAPI:
    app = fastapi.FastAPI()
    app.add_middleware(middleware.OriginCheckMiddleware)

    @app.post("/unsafe")
    async def _post_unsafe() -> dict[str, bool]:
        return {"ok": True}

    @app.get("/safe")
    async def _get_safe() -> dict[str, bool]:
        return {"ok": True}

    return app


@pytest.fixture
def origin_check_client(monkeypatch):
    monkeypatch.setattr(SETTINGS, "examomatic_host", _EXAMOMATIC_HOST)
    return fastapi.testclient.TestClient(_make_app(), base_url=_DEVICE_ORIGIN)


def test_origin_matching_request_host_is_allowed(origin_check_client):
    response = origin_check_client.post("/unsafe", headers={"origin": _DEVICE_ORIGIN})

    assert response.status_code == 200


def test_examomatic_origin_is_allowed_even_though_host_differs(origin_check_client):
    # Reproduces Exam-O-Matic's VPN-proxied invigilator requests (see
    # README's connection diagram): the browser's Origin stays
    # Exam-O-Matic's own throughout, while the request's Host (and thus
    # request.url.hostname) is the device's own fqdn.
    response = origin_check_client.post(
        "/unsafe", headers={"origin": _EXAMOMATIC_ORIGIN}
    )

    assert response.status_code == 200


def test_examomatic_origin_via_referer_fallback_is_allowed(origin_check_client):
    response = origin_check_client.post(
        "/unsafe",
        headers={"referer": f"{_EXAMOMATIC_ORIGIN}/remote/12345/invigilator/"},
    )

    assert response.status_code == 200


def test_unrelated_origin_is_rejected(origin_check_client):
    response = origin_check_client.post(
        "/unsafe", headers={"origin": "https://attacker.example:8443"}
    )

    assert response.status_code == 403


def test_missing_origin_and_referer_is_rejected(origin_check_client):
    response = origin_check_client.post("/unsafe")

    assert response.status_code == 403


def test_safe_methods_bypass_origin_check(origin_check_client):
    response = origin_check_client.get(
        "/safe", headers={"origin": "https://attacker.example"}
    )

    assert response.status_code == 200
