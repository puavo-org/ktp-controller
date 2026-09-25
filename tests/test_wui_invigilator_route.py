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
    assert b"alice" in response.content
    assert b'action="/logout"' in response.content


_STUDENT_UUID = "0b7f4c5e-2a55-4c34-9a8c-7e4f0d3a1b21"
_SESSION_UUID = "5d2e8f1a-6b3c-4d9e-8f7a-1c2b3d4e5f60"


def _raw_abitti2_stats_messages():
    return [
        {
            "data": {
                "students": [
                    {
                        "studentUuid": _STUDENT_UUID,
                        "sessionUuid": _SESSION_UUID,
                        "firstNames": "Maija",
                        "lastName": "Meikäläinen",
                        "studentBd": "010105",
                        "studentStatus": "exam-in-progress",
                        "sessionStatus": "exam_in_progress",
                        "updateTime": None,
                        "examFinishedAt": None,
                        "examTitle": "Matematiikka",
                    }
                ]
            }
        }
    ]


def test_invigilator_view_renders_student_without_uuid_columns(
    wui_client, override_session, mocker
):
    mocker.patch(
        "ktp_controller.api.client.get_raw_abitti2_stats_messages",
        return_value=_raw_abitti2_stats_messages(),
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
    assert "Maija Meikäläinen" in response.text
    assert "Student uuid" not in response.text
    assert "Session uuid" not in response.text


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


def test_invigilator_ws_rejects_without_session(wui_client, mocker):
    mocker.patch(
        "ktp_controller.wui.auth.get_current_session",
        side_effect=ktp_controller.wui.auth.NotAuthenticatedError,
    )

    with pytest.raises(starlette.testclient.WebSocketDisconnect) as exc_info:
        with wui_client.websocket_connect("/invigilator/ws"):
            pass

    assert exc_info.value.code == 4401


def test_invigilator_ws_rejects_without_permission(wui_client, mocker):
    mocker.patch(
        "ktp_controller.wui.auth.get_current_session",
        return_value=ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset(),
        ),
    )

    with pytest.raises(starlette.testclient.WebSocketDisconnect) as exc_info:
        with wui_client.websocket_connect("/invigilator/ws"):
            pass

    assert exc_info.value.code == 4403


def test_invigilator_ws_registers_and_unregisters(wui_client, mocker):
    mocker.patch(
        "ktp_controller.wui.auth.get_current_session",
        return_value=ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.invigilator.view"}),
        ),
    )
    register_mock = mocker.patch.object(
        ktp_controller.wui.main.APP.state.invigilator_ws_registry,
        "register",
        new=mocker.AsyncMock(),
    )
    unregister_mock = mocker.patch.object(
        ktp_controller.wui.main.APP.state.invigilator_ws_registry,
        "unregister",
        new=mocker.AsyncMock(),
    )

    with wui_client.websocket_connect("/invigilator/ws"):
        pass

    register_mock.assert_awaited_once()
    unregister_mock.assert_awaited_once()


_SAME_ORIGIN_HEADERS = {"origin": "http://testserver"}
_END_EXAM_FORM = {"session_uuid": _SESSION_UUID, "student_uuid": _STUDENT_UUID}


def test_invigilator_view_shows_end_exam_button_with_permission(
    wui_client, override_session, mocker
):
    mocker.patch(
        "ktp_controller.api.client.get_raw_abitti2_stats_messages",
        return_value=_raw_abitti2_stats_messages(),
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.invigilator.view", "wui.invigilator.end-exam"}),
        )
    )

    response = wui_client.get("/invigilator/")

    assert response.status_code == 200
    assert 'hx-post="/invigilator/actions/end-exam"' in response.text
    assert _STUDENT_UUID in response.text
    assert _SESSION_UUID in response.text


def test_invigilator_view_hides_end_exam_button_without_permission(
    wui_client, override_session, mocker
):
    mocker.patch(
        "ktp_controller.api.client.get_raw_abitti2_stats_messages",
        return_value=_raw_abitti2_stats_messages(),
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
    assert "/invigilator/actions/end-exam" not in response.text


def test_end_exam_requires_login(wui_client, mocker):
    end_student_exam_mock = mocker.patch(
        "ktp_controller.abitti2.client.end_student_exam", new=mocker.AsyncMock()
    )

    response = wui_client.post(
        "/invigilator/actions/end-exam",
        data=_END_EXAM_FORM,
        headers=_SAME_ORIGIN_HEADERS,
    )

    assert response.status_code == 303
    assert response.headers["location"].startswith("/login")
    end_student_exam_mock.assert_not_called()


def test_end_exam_forbidden_without_permission(wui_client, override_session, mocker):
    end_student_exam_mock = mocker.patch(
        "ktp_controller.abitti2.client.end_student_exam", new=mocker.AsyncMock()
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.invigilator.view"}),
        )
    )

    response = wui_client.post(
        "/invigilator/actions/end-exam",
        data=_END_EXAM_FORM,
        headers=_SAME_ORIGIN_HEADERS,
    )

    assert response.status_code == 403
    end_student_exam_mock.assert_not_called()


def test_end_exam_calls_abitti2(wui_client, override_session, mocker):
    end_student_exam_mock = mocker.patch(
        "ktp_controller.abitti2.client.end_student_exam", new=mocker.AsyncMock()
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.invigilator.end-exam"}),
        )
    )

    response = wui_client.post(
        "/invigilator/actions/end-exam",
        data=_END_EXAM_FORM,
        headers=_SAME_ORIGIN_HEADERS,
    )

    assert response.status_code == 202
    assert response.content == b""
    end_student_exam_mock.assert_awaited_once_with(
        session_uuid=_SESSION_UUID, student_uuid=_STUDENT_UUID
    )


def test_end_exam_rejects_invalid_uuid(wui_client, override_session, mocker):
    end_student_exam_mock = mocker.patch(
        "ktp_controller.abitti2.client.end_student_exam", new=mocker.AsyncMock()
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.invigilator.end-exam"}),
        )
    )

    response = wui_client.post(
        "/invigilator/actions/end-exam",
        data={**_END_EXAM_FORM, "student_uuid": "not-a-uuid"},
        headers=_SAME_ORIGIN_HEADERS,
    )

    assert response.status_code == 422
    end_student_exam_mock.assert_not_called()


def test_end_exam_logs_abitti2_failure(wui_client, override_session, mocker, caplog):
    mocker.patch(
        "ktp_controller.abitti2.client.end_student_exam",
        new=mocker.AsyncMock(side_effect=RuntimeError("abitti2 is down")),
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.invigilator.end-exam"}),
        )
    )

    response = wui_client.post(
        "/invigilator/actions/end-exam",
        data=_END_EXAM_FORM,
        headers=_SAME_ORIGIN_HEADERS,
    )

    assert response.status_code == 202
    assert any(
        record.levelname == "ERROR"
        and "Failed to end exam" in record.getMessage()
        and record.exc_info is not None
        for record in caplog.records
    )
