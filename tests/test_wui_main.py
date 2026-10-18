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
    response = wui_client.get("/", headers={"X-Forwarded-Prefix": "/remote/12345"})

    assert response.status_code == 303
    assert response.headers["location"] == "/remote/12345/invigilator/"


def test_get_root_redirect_ignores_malformed_forwarded_prefix(wui_client):
    response = wui_client.get("/", headers={"X-Forwarded-Prefix": "/not-remote/12345"})

    assert response.status_code == 303
    assert response.headers["location"] == "/invigilator/"
