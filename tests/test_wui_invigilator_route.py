import fastapi.testclient
import pytest

import ktp_controller.wui.auth
import ktp_controller.wui.main


@pytest.fixture
def wui_client():
    return fastapi.testclient.TestClient(
        ktp_controller.wui.main.APP, follow_redirects=False
    )


@pytest.fixture
def override_session():
    def _override(session):
        def _get_current_session():
            return session

        ktp_controller.wui.main.APP.dependency_overrides[
            ktp_controller.wui.auth.get_current_session
        ] = _get_current_session

    yield _override
    ktp_controller.wui.main.APP.dependency_overrides.clear()


def test_invigilator_view_requires_login(wui_client):
    response = wui_client.get("/invigilator/")

    assert response.status_code == 303
    assert response.headers["location"].startswith("/login")


def test_invigilator_view_allowed_with_permission(wui_client, override_session, mocker):
    mocker.patch(
        "ktp_controller.api.client.get_raw_abitti2_stats_messages",
        return_value=[],
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.invigilator.view"}),
        )
    )

    response = wui_client.get("/invigilator/")

    assert response.status_code == 200


def test_invigilator_view_forbidden_without_permission(wui_client, override_session):
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset(),
        )
    )

    response = wui_client.get("/invigilator/")

    assert response.status_code == 403
