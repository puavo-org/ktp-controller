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
