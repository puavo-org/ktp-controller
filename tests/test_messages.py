import pydantic
import pytest

import ktp_controller.messages

_SET_BROWSER_PERMISSION_COMMAND = (
    ktp_controller.messages.Command.SET_EXAM_SESSION_PERMISSION_TO_USE_BROWSERS
)


@pytest.mark.parametrize(
    ("validate", "payload"),
    [
        pytest.param(
            ktp_controller.messages.SimpleCommandData.model_validate,
            {
                "command": ktp_controller.messages.Command.CHANGE_STUDENT_ACCESS_CODE,
                "session_uuid": "some-uuid",
                "allow": True,
            },
            id="simple_command_data_rejects_session_uuid_and_allow",
        ),
        pytest.param(
            ktp_controller.messages.SimpleCommandData.model_validate,
            {"command": _SET_BROWSER_PERMISSION_COMMAND},
            id="simple_command_data_rejects_set_exam_session_permission_command",
        ),
        pytest.param(
            (
                ktp_controller.messages.SetExamSessionPermissionToUseBrowsersCommandData
            ).model_validate,
            {"command": _SET_BROWSER_PERMISSION_COMMAND},
            id="set_exam_session_permission_to_use_browsers_command_data_requires_payload",
        ),
        pytest.param(
            (
                ktp_controller.messages.SetExamSessionPermissionToUseBrowsersCommandData
            ).model_validate,
            {
                "command": _SET_BROWSER_PERMISSION_COMMAND,
                "session_uuid": "some-uuid",
                "allow": True,
            },
            id="set_exam_session_permission_to_use_browsers_command_data_requires_student_uuid",
        ),
        pytest.param(
            ktp_controller.messages.CommandDataAdapter.validate_python,
            {"command": "not_a_real_command"},
            id="command_data_adapter_rejects_unknown_command",
        ),
        pytest.param(
            ktp_controller.messages.SimpleCommandData.model_validate,
            {"command": ktp_controller.messages.Command.ALLOW_AUDIO_REPLAY},
            id="simple_command_data_rejects_allow_audio_replay_command",
        ),
        pytest.param(
            ktp_controller.messages.AllowAudioReplayCommandData.model_validate,
            {"command": ktp_controller.messages.Command.ALLOW_AUDIO_REPLAY},
            id="allow_audio_replay_command_data_requires_student_uuid",
        ),
        pytest.param(
            ktp_controller.messages.SimpleCommandData.model_validate,
            {"command": ktp_controller.messages.Command.END_STUDENT_EXAM},
            id="simple_command_data_rejects_end_student_exam_command",
        ),
        pytest.param(
            ktp_controller.messages.EndStudentExamCommandData.model_validate,
            {"command": ktp_controller.messages.Command.END_STUDENT_EXAM},
            id="end_student_exam_command_data_requires_payload",
        ),
        pytest.param(
            ktp_controller.messages.EndStudentExamCommandData.model_validate,
            {
                "command": ktp_controller.messages.Command.END_STUDENT_EXAM,
                "session_uuid": "some-uuid",
            },
            id="end_student_exam_command_data_requires_student_uuid",
        ),
    ],
)
def test_command_data_rejects_invalid_payload(validate, payload):
    with pytest.raises(pydantic.ValidationError):
        validate(payload)


@pytest.mark.parametrize(
    ("payload", "expected_class", "expected_fields"),
    [
        pytest.param(
            {"command": ktp_controller.messages.Command.CHANGE_STUDENT_ACCESS_CODE},
            ktp_controller.messages.SimpleCommandData,
            {},
            id="simple_command",
        ),
        pytest.param(
            {
                "command": _SET_BROWSER_PERMISSION_COMMAND,
                "session_uuid": "some-uuid",
                "student_uuid": "some-student-uuid",
                "allow": True,
            },
            ktp_controller.messages.SetExamSessionPermissionToUseBrowsersCommandData,
            {
                "session_uuid": "some-uuid",
                "student_uuid": "some-student-uuid",
                "allow": True,
            },
            id="set_exam_session_permission_command",
        ),
        pytest.param(
            {
                "command": ktp_controller.messages.Command.ALLOW_AUDIO_REPLAY,
                "student_uuid": "some-student-uuid",
            },
            ktp_controller.messages.AllowAudioReplayCommandData,
            {"student_uuid": "some-student-uuid"},
            id="allow_audio_replay_command",
        ),
        pytest.param(
            {
                "command": ktp_controller.messages.Command.END_STUDENT_EXAM,
                "session_uuid": "some-uuid",
                "student_uuid": "some-student-uuid",
            },
            ktp_controller.messages.EndStudentExamCommandData,
            {"session_uuid": "some-uuid", "student_uuid": "some-student-uuid"},
            id="end_student_exam_command",
        ),
    ],
)
def test_command_data_adapter_discriminates_command(
    payload, expected_class, expected_fields
):
    command_data = ktp_controller.messages.CommandDataAdapter.validate_python(payload)

    assert isinstance(command_data, expected_class)
    for field, value in expected_fields.items():
        assert getattr(command_data, field) == value
