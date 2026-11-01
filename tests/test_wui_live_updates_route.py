import datetime
import re

import fastapi.testclient
import pytest
import starlette.testclient

import ktp_controller.wui.auth
import ktp_controller.wui.main


def _nav_item_tag(html, link_text):
    for match in re.finditer(r"<li[^>]*>(?:(?!</li>).)*?</li>", html, re.DOTALL):
        if link_text in match.group(0):
            return match.group(0)
    raise AssertionError(f"nav item for {link_text!r} not found in response")


@pytest.fixture
def wui_client():
    return fastapi.testclient.TestClient(
        ktp_controller.wui.main.APP, follow_redirects=False
    )


@pytest.fixture(autouse=True)
def _mock_last_status_report(mocker):
    mocker.patch("ktp_controller.api.client.get_last_status_report", return_value=None)


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


def test_ws_rejects_without_session(wui_client, mocker):
    mocker.patch(
        "ktp_controller.wui.auth.get_current_session",
        side_effect=ktp_controller.wui.auth.NotAuthenticatedError,
    )

    with pytest.raises(starlette.testclient.WebSocketDisconnect) as exc_info:
        with wui_client.websocket_connect("/ws"):
            pass

    assert exc_info.value.code == 4401


def test_ws_rejects_without_permission(wui_client, mocker):
    mocker.patch(
        "ktp_controller.wui.auth.get_current_session",
        return_value=ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset(),
        ),
    )

    with pytest.raises(starlette.testclient.WebSocketDisconnect) as exc_info:
        with wui_client.websocket_connect("/ws"):
            pass

    assert exc_info.value.code == 4403


def test_ws_registers_and_unregisters(wui_client, mocker):
    mocker.patch(
        "ktp_controller.wui.auth.get_current_session",
        return_value=ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.invigilator.view"}),
        ),
    )
    register_mock = mocker.patch.object(
        ktp_controller.wui.main.APP.state.live_update_registry,
        "register",
        new=mocker.AsyncMock(),
    )
    unregister_mock = mocker.patch.object(
        ktp_controller.wui.main.APP.state.live_update_registry,
        "unregister",
        new=mocker.AsyncMock(),
    )

    with wui_client.websocket_connect("/ws"):
        pass

    register_mock.assert_awaited_once()
    unregister_mock.assert_awaited_once()


def test_ws_accepts_with_only_landing_permission(wui_client, mocker):
    mocker.patch(
        "ktp_controller.wui.auth.get_current_session",
        return_value=ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.landing.view"}),
        ),
    )
    register_mock = mocker.patch.object(
        ktp_controller.wui.main.APP.state.live_update_registry,
        "register",
        new=mocker.AsyncMock(),
    )
    unregister_mock = mocker.patch.object(
        ktp_controller.wui.main.APP.state.live_update_registry,
        "unregister",
        new=mocker.AsyncMock(),
    )

    with wui_client.websocket_connect("/ws"):
        pass

    register_mock.assert_awaited_once()
    unregister_mock.assert_awaited_once()


def test_nav_status_requires_login(wui_client):
    response = wui_client.get("/nav_status")

    assert response.status_code == 303
    assert response.headers["location"].startswith("/login")


def test_nav_status_forbidden_without_either_view_permission(
    wui_client, override_session
):
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset(),
        )
    )

    response = wui_client.get("/nav_status")

    assert response.status_code == 403


@pytest.mark.parametrize("permission", ["wui.invigilator.view", "wui.landing.view"])
def test_nav_status_allowed_with_either_view_permission(
    wui_client, override_session, permission
):
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({permission}),
            locale="en",
        )
    )

    response = wui_client.get("/nav_status")

    assert response.status_code == 200
    nav_item = _nav_item_tag(response.text, "Exam server")
    assert "value-warning" not in nav_item
    assert "severity-icon" not in nav_item


def test_nav_status_shows_warning_for_soon_expiring_cert(
    wui_client, override_session, mocker, make_status_report
):
    mocker.patch(
        "ktp_controller.api.client.get_last_status_report",
        return_value=make_status_report(
            abitti2_cert_expires_at=(
                datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=1)
            ).isoformat()
        ),
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.landing.view"}),
            locale="en",
        )
    )

    response = wui_client.get("/nav_status")

    assert response.status_code == 200
    nav_item = _nav_item_tag(response.text, "Exam server")
    assert "value-warning" in nav_item
    assert "severity-icon" in nav_item


def test_nav_status_marks_current_when_on_landing_page(wui_client, override_session):
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.landing.view"}),
            locale="en",
        )
    )

    response = wui_client.get(
        "/nav_status", headers={"HX-Current-URL": "http://testserver/"}
    )

    assert response.status_code == 200
    nav_item = _nav_item_tag(response.text, "Exam server")
    assert 'aria-current="page"' in nav_item


def test_nav_status_not_current_when_on_another_page(wui_client, override_session):
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.landing.view"}),
            locale="en",
        )
    )

    response = wui_client.get(
        "/nav_status",
        headers={"HX-Current-URL": "http://testserver/invigilator/"},
    )

    assert response.status_code == 200
    nav_item = _nav_item_tag(response.text, "Exam server")
    assert "aria-current" not in nav_item
