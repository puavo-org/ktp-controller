import dataclasses

import pytest

import ktp_controller.messages
import ktp_controller.wui.auth
import ktp_controller.wui.main

_SAME_ORIGIN_HEADERS = {"origin": "http://testserver"}
_STUDENT_UUID = "0b7f4c5e-2a55-4c34-9a8c-7e4f0d3a1b21"
_SESSION_UUID = "5d2e8f1a-6b3c-4d9e-8f7a-1c2b3d4e5f60"


@dataclasses.dataclass(frozen=True)
class _Action:
    path: str
    form: dict
    permission: str
    command: ktp_controller.messages.Command
    command_kwargs: dict
    uuid_field: str | None = None
    log_message: str | None = None


_ACTIONS = [
    _Action(
        path="/actions/end-exam",
        form={"session_uuid": _SESSION_UUID, "student_uuid": _STUDENT_UUID},
        permission="wui.actions.end-exam",
        command=ktp_controller.messages.Command.END_STUDENT_EXAM,
        command_kwargs={"session_uuid": _SESSION_UUID, "student_uuid": _STUDENT_UUID},
        uuid_field="student_uuid",
        log_message="Failed to end exam",
    ),
    _Action(
        path="/actions/change-student-access-code",
        form={},
        permission="wui.actions.change-student-access-code",
        command=ktp_controller.messages.Command.CHANGE_STUDENT_ACCESS_CODE,
        command_kwargs={},
    ),
    _Action(
        path="/actions/set-exam-session-permission-to-use-browsers",
        form={
            "session_uuid": _SESSION_UUID,
            "student_uuid": _STUDENT_UUID,
            "allow": "true",
        },
        permission="wui.actions.set-exam-session-permission-to-use-browsers",
        command=(
            ktp_controller.messages.Command.SET_EXAM_SESSION_PERMISSION_TO_USE_BROWSERS
        ),
        command_kwargs={
            "session_uuid": _SESSION_UUID,
            "student_uuid": _STUDENT_UUID,
            "allow": True,
        },
        uuid_field="session_uuid",
        log_message="Failed to set browser-use permission",
    ),
    _Action(
        path="/actions/allow-audio-replay",
        form={"student_uuid": _STUDENT_UUID},
        permission="wui.actions.allow-audio-replay",
        command=ktp_controller.messages.Command.ALLOW_AUDIO_REPLAY,
        command_kwargs={"student_uuid": _STUDENT_UUID},
        uuid_field="student_uuid",
        log_message="Failed to allow audio replay",
    ),
]


def _action_id(action):
    return action.path.removeprefix("/actions/")


@pytest.mark.parametrize("action", _ACTIONS, ids=_action_id)
def test_action_requires_login(wui_client, mocker, action):
    async_command_mock = mocker.patch(
        "ktp_controller.api.client.async_command", new=mocker.AsyncMock()
    )

    response = wui_client.post(
        action.path, data=action.form, headers=_SAME_ORIGIN_HEADERS
    )

    assert response.status_code == 303
    assert response.headers["location"].startswith("/login")
    async_command_mock.assert_not_called()


@pytest.mark.parametrize("action", _ACTIONS, ids=_action_id)
def test_action_forbidden_without_permission(
    wui_client, override_session, mocker, action
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
        action.path, data=action.form, headers=_SAME_ORIGIN_HEADERS
    )

    assert response.status_code == 403
    async_command_mock.assert_not_called()


@pytest.mark.parametrize("action", _ACTIONS, ids=_action_id)
def test_action_calls_api(wui_client, override_session, mocker, action):
    async_command_mock = mocker.patch(
        "ktp_controller.api.client.async_command", new=mocker.AsyncMock()
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({action.permission}),
        )
    )

    response = wui_client.post(
        action.path, data=action.form, headers=_SAME_ORIGIN_HEADERS
    )

    assert response.status_code == 202
    assert response.content == b""
    async_command_mock.assert_awaited_once_with(action.command, **action.command_kwargs)


@pytest.mark.parametrize(
    "action", [a for a in _ACTIONS if a.uuid_field is not None], ids=_action_id
)
def test_action_rejects_invalid_uuid(wui_client, override_session, mocker, action):
    async_command_mock = mocker.patch(
        "ktp_controller.api.client.async_command", new=mocker.AsyncMock()
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({action.permission}),
        )
    )

    response = wui_client.post(
        action.path,
        data={**action.form, action.uuid_field: "not-a-uuid"},
        headers=_SAME_ORIGIN_HEADERS,
    )

    assert response.status_code == 422
    async_command_mock.assert_not_called()


@pytest.mark.parametrize("action", _ACTIONS, ids=_action_id)
def test_action_logs_api_failure(wui_client, override_session, mocker, caplog, action):
    mocker.patch(
        "ktp_controller.api.client.async_command",
        side_effect=RuntimeError("boom"),
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({action.permission}),
        )
    )

    response = wui_client.post(
        action.path, data=action.form, headers=_SAME_ORIGIN_HEADERS
    )

    assert response.status_code == 202
    if action.log_message is not None:
        assert any(
            record.levelname == "ERROR"
            and action.log_message in record.getMessage()
            and record.exc_info is not None
            for record in caplog.records
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
