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


def _make_root_path_app() -> fastapi.FastAPI:
    app = fastapi.FastAPI()
    app.add_middleware(middleware.RootPathFromHeaderMiddleware)

    @app.get("/thing")
    async def _get_thing(request: fastapi.Request) -> dict[str, str]:
        return {"root_path": request.scope["root_path"]}

    return app


@pytest.fixture
def root_path_client(monkeypatch):
    monkeypatch.setattr(SETTINGS, "id", 12345)
    return fastapi.testclient.TestClient(_make_root_path_app())


def test_missing_forwarded_prefix_header_is_passed_through(root_path_client):
    response = root_path_client.get("/thing")

    assert response.status_code == 200
    assert response.json() == {"root_path": ""}


def test_matching_forwarded_prefix_sets_root_path(root_path_client):
    response = root_path_client.get(
        "/thing", headers={"x-forwarded-prefix": "/remote/12345"}
    )

    assert response.status_code == 200
    assert response.json() == {"root_path": "/remote/12345"}


def test_forwarded_prefix_with_wrong_id_is_rejected(root_path_client):
    response = root_path_client.get(
        "/thing", headers={"x-forwarded-prefix": "/remote/99999"}
    )

    assert response.status_code == 403


def test_malformed_forwarded_prefix_is_rejected(root_path_client):
    response = root_path_client.get(
        "/thing", headers={"x-forwarded-prefix": "/not-a-valid-prefix"}
    )

    assert response.status_code == 403
