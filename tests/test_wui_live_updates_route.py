import fastapi.testclient
import pytest
import starlette.testclient

import ktp_controller.wui.auth
import ktp_controller.wui.main


@pytest.fixture
def wui_client():
    return fastapi.testclient.TestClient(
        ktp_controller.wui.main.APP, follow_redirects=False
    )


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
