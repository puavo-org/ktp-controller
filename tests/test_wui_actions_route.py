import fastapi.testclient
import pytest

import ktp_controller.messages
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


_SAME_ORIGIN_HEADERS = {"origin": "http://testserver"}
_STUDENT_UUID = "0b7f4c5e-2a55-4c34-9a8c-7e4f0d3a1b21"
_SESSION_UUID = "5d2e8f1a-6b3c-4d9e-8f7a-1c2b3d4e5f60"
_END_EXAM_FORM = {"session_uuid": _SESSION_UUID, "student_uuid": _STUDENT_UUID}


def test_end_exam_requires_login(wui_client, mocker):
    async_command_mock = mocker.patch(
        "ktp_controller.api.client.async_command", new=mocker.AsyncMock()
    )

    response = wui_client.post(
        "/actions/end-exam",
        data=_END_EXAM_FORM,
        headers=_SAME_ORIGIN_HEADERS,
    )

    assert response.status_code == 303
    assert response.headers["location"].startswith("/login")
    async_command_mock.assert_not_called()


def test_end_exam_forbidden_without_permission(wui_client, override_session, mocker):
    async_command_mock = mocker.patch(
        "ktp_controller.api.client.async_command", new=mocker.AsyncMock()
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.invigilator.view"}),
        )
    )

    response = wui_client.post(
        "/actions/end-exam",
        data=_END_EXAM_FORM,
        headers=_SAME_ORIGIN_HEADERS,
    )

    assert response.status_code == 403
    async_command_mock.assert_not_called()


def test_end_exam_calls_api(wui_client, override_session, mocker):
    async_command_mock = mocker.patch(
        "ktp_controller.api.client.async_command", new=mocker.AsyncMock()
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.actions.end-exam"}),
        )
    )

    response = wui_client.post(
        "/actions/end-exam",
        data=_END_EXAM_FORM,
        headers=_SAME_ORIGIN_HEADERS,
    )

    assert response.status_code == 202
    assert response.content == b""
    async_command_mock.assert_awaited_once_with(
        ktp_controller.messages.Command.END_STUDENT_EXAM,
        session_uuid=_SESSION_UUID,
        student_uuid=_STUDENT_UUID,
    )


def test_end_exam_rejects_invalid_uuid(wui_client, override_session, mocker):
    async_command_mock = mocker.patch(
        "ktp_controller.api.client.async_command", new=mocker.AsyncMock()
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.actions.end-exam"}),
        )
    )

    response = wui_client.post(
        "/actions/end-exam",
        data={**_END_EXAM_FORM, "student_uuid": "not-a-uuid"},
        headers=_SAME_ORIGIN_HEADERS,
    )

    assert response.status_code == 422
    async_command_mock.assert_not_called()


def test_end_exam_logs_api_failure(wui_client, override_session, mocker, caplog):
    mocker.patch(
        "ktp_controller.api.client.async_command",
        side_effect=RuntimeError("abitti2 is down"),
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.actions.end-exam"}),
        )
    )

    response = wui_client.post(
        "/actions/end-exam",
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


def test_change_student_access_code_requires_login(wui_client, mocker):
    async_command_mock = mocker.patch(
        "ktp_controller.api.client.async_command", new=mocker.AsyncMock()
    )

    response = wui_client.post(
        "/actions/change-student-access-code",
        headers=_SAME_ORIGIN_HEADERS,
    )

    assert response.status_code == 303
    assert response.headers["location"].startswith("/login")
    async_command_mock.assert_not_called()


def test_change_student_access_code_forbidden_without_permission(
    wui_client, override_session, mocker
):
    async_command_mock = mocker.patch(
        "ktp_controller.api.client.async_command", new=mocker.AsyncMock()
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.invigilator.view"}),
        )
    )

    response = wui_client.post(
        "/actions/change-student-access-code",
        headers=_SAME_ORIGIN_HEADERS,
    )

    assert response.status_code == 403
    async_command_mock.assert_not_called()


def test_change_student_access_code_calls_api(wui_client, override_session, mocker):
    async_command_mock = mocker.patch(
        "ktp_controller.api.client.async_command", new=mocker.AsyncMock()
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.actions.change-student-access-code"}),
        )
    )

    response = wui_client.post(
        "/actions/change-student-access-code",
        headers=_SAME_ORIGIN_HEADERS,
    )

    assert response.status_code == 202
    assert response.content == b""
    async_command_mock.assert_awaited_once_with(
        ktp_controller.messages.Command.CHANGE_STUDENT_ACCESS_CODE
    )


def test_change_student_access_code_logs_api_failure(
    wui_client, override_session, mocker
):
    mocker.patch(
        "ktp_controller.api.client.async_command",
        side_effect=RuntimeError("boom"),
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.actions.change-student-access-code"}),
        )
    )

    response = wui_client.post(
        "/actions/change-student-access-code",
        headers=_SAME_ORIGIN_HEADERS,
    )

    assert response.status_code == 202


_SET_BROWSER_PERMISSION_FORM = {
    "session_uuid": _SESSION_UUID,
    "student_uuid": _STUDENT_UUID,
    "allow": "true",
}


def test_set_exam_session_permission_to_use_browsers_requires_login(wui_client, mocker):
    async_command_mock = mocker.patch(
        "ktp_controller.api.client.async_command", new=mocker.AsyncMock()
    )

    response = wui_client.post(
        "/actions/set-exam-session-permission-to-use-browsers",
        data=_SET_BROWSER_PERMISSION_FORM,
        headers=_SAME_ORIGIN_HEADERS,
    )

    assert response.status_code == 303
    assert response.headers["location"].startswith("/login")
    async_command_mock.assert_not_called()


def test_set_exam_session_permission_to_use_browsers_forbidden_without_permission(
    wui_client, override_session, mocker
):
    async_command_mock = mocker.patch(
        "ktp_controller.api.client.async_command", new=mocker.AsyncMock()
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.invigilator.view"}),
        )
    )

    response = wui_client.post(
        "/actions/set-exam-session-permission-to-use-browsers",
        data=_SET_BROWSER_PERMISSION_FORM,
        headers=_SAME_ORIGIN_HEADERS,
    )

    assert response.status_code == 403
    async_command_mock.assert_not_called()


def test_set_exam_session_permission_to_use_browsers_calls_api(
    wui_client, override_session, mocker
):
    async_command_mock = mocker.patch(
        "ktp_controller.api.client.async_command", new=mocker.AsyncMock()
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset(
                {"wui.actions.set-exam-session-permission-to-use-browsers"}
            ),
        )
    )

    response = wui_client.post(
        "/actions/set-exam-session-permission-to-use-browsers",
        data=_SET_BROWSER_PERMISSION_FORM,
        headers=_SAME_ORIGIN_HEADERS,
    )

    assert response.status_code == 202
    assert response.content == b""
    async_command_mock.assert_awaited_once_with(
        ktp_controller.messages.Command.SET_EXAM_SESSION_PERMISSION_TO_USE_BROWSERS,
        session_uuid=_SESSION_UUID,
        student_uuid=_STUDENT_UUID,
        allow=True,
    )


def test_set_exam_session_permission_to_use_browsers_unchecked_means_disallow(
    wui_client, override_session, mocker
):
    # A checkbox is only submitted when checked, per standard HTML form
    # semantics, so unchecking it means the "allow" field is simply absent
    # from the request.
    async_command_mock = mocker.patch(
        "ktp_controller.api.client.async_command", new=mocker.AsyncMock()
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset(
                {"wui.actions.set-exam-session-permission-to-use-browsers"}
            ),
        )
    )

    response = wui_client.post(
        "/actions/set-exam-session-permission-to-use-browsers",
        data={"session_uuid": _SESSION_UUID, "student_uuid": _STUDENT_UUID},
        headers=_SAME_ORIGIN_HEADERS,
    )

    assert response.status_code == 202
    async_command_mock.assert_awaited_once_with(
        ktp_controller.messages.Command.SET_EXAM_SESSION_PERMISSION_TO_USE_BROWSERS,
        session_uuid=_SESSION_UUID,
        student_uuid=_STUDENT_UUID,
        allow=False,
    )


def test_set_exam_session_permission_to_use_browsers_rejects_invalid_uuid(
    wui_client, override_session, mocker
):
    async_command_mock = mocker.patch(
        "ktp_controller.api.client.async_command", new=mocker.AsyncMock()
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset(
                {"wui.actions.set-exam-session-permission-to-use-browsers"}
            ),
        )
    )

    response = wui_client.post(
        "/actions/set-exam-session-permission-to-use-browsers",
        data={
            "session_uuid": "not-a-uuid",
            "student_uuid": _STUDENT_UUID,
            "allow": "true",
        },
        headers=_SAME_ORIGIN_HEADERS,
    )

    assert response.status_code == 422
    async_command_mock.assert_not_called()


def test_set_exam_session_permission_to_use_browsers_logs_api_failure(
    wui_client, override_session, mocker, caplog
):
    mocker.patch(
        "ktp_controller.api.client.async_command",
        side_effect=RuntimeError("boom"),
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset(
                {"wui.actions.set-exam-session-permission-to-use-browsers"}
            ),
        )
    )

    response = wui_client.post(
        "/actions/set-exam-session-permission-to-use-browsers",
        data=_SET_BROWSER_PERMISSION_FORM,
        headers=_SAME_ORIGIN_HEADERS,
    )

    assert response.status_code == 202
    assert any(
        record.levelname == "ERROR"
        and "Failed to set browser-use permission" in record.getMessage()
        and record.exc_info is not None
        for record in caplog.records
    )


_ALLOW_AUDIO_REPLAY_FORM = {"student_uuid": _STUDENT_UUID}


def test_allow_audio_replay_requires_login(wui_client, mocker):
    async_command_mock = mocker.patch(
        "ktp_controller.api.client.async_command", new=mocker.AsyncMock()
    )

    response = wui_client.post(
        "/actions/allow-audio-replay",
        data=_ALLOW_AUDIO_REPLAY_FORM,
        headers=_SAME_ORIGIN_HEADERS,
    )

    assert response.status_code == 303
    assert response.headers["location"].startswith("/login")
    async_command_mock.assert_not_called()


def test_allow_audio_replay_forbidden_without_permission(
    wui_client, override_session, mocker
):
    async_command_mock = mocker.patch(
        "ktp_controller.api.client.async_command", new=mocker.AsyncMock()
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.invigilator.view"}),
        )
    )

    response = wui_client.post(
        "/actions/allow-audio-replay",
        data=_ALLOW_AUDIO_REPLAY_FORM,
        headers=_SAME_ORIGIN_HEADERS,
    )

    assert response.status_code == 403
    async_command_mock.assert_not_called()


def test_allow_audio_replay_calls_api(wui_client, override_session, mocker):
    async_command_mock = mocker.patch(
        "ktp_controller.api.client.async_command", new=mocker.AsyncMock()
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.actions.allow-audio-replay"}),
        )
    )

    response = wui_client.post(
        "/actions/allow-audio-replay",
        data=_ALLOW_AUDIO_REPLAY_FORM,
        headers=_SAME_ORIGIN_HEADERS,
    )

    assert response.status_code == 202
    assert response.content == b""
    async_command_mock.assert_awaited_once_with(
        ktp_controller.messages.Command.ALLOW_AUDIO_REPLAY,
        student_uuid=_STUDENT_UUID,
    )


def test_allow_audio_replay_rejects_invalid_uuid(wui_client, override_session, mocker):
    async_command_mock = mocker.patch(
        "ktp_controller.api.client.async_command", new=mocker.AsyncMock()
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.actions.allow-audio-replay"}),
        )
    )

    response = wui_client.post(
        "/actions/allow-audio-replay",
        data={"student_uuid": "not-a-uuid"},
        headers=_SAME_ORIGIN_HEADERS,
    )

    assert response.status_code == 422
    async_command_mock.assert_not_called()


def test_allow_audio_replay_logs_api_failure(
    wui_client, override_session, mocker, caplog
):
    mocker.patch(
        "ktp_controller.api.client.async_command",
        side_effect=RuntimeError("boom"),
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.actions.allow-audio-replay"}),
        )
    )

    response = wui_client.post(
        "/actions/allow-audio-replay",
        data=_ALLOW_AUDIO_REPLAY_FORM,
        headers=_SAME_ORIGIN_HEADERS,
    )

    assert response.status_code == 202
    assert any(
        record.levelname == "ERROR"
        and "Failed to allow audio replay" in record.getMessage()
        and record.exc_info is not None
        for record in caplog.records
    )
