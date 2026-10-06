import pydantic
import pytest

import ktp_controller.messages


def test_simple_command_data_rejects_session_uuid_and_allow():
    with pytest.raises(pydantic.ValidationError):
        ktp_controller.messages.SimpleCommandData.model_validate(
            {
                "command": ktp_controller.messages.Command.CHANGE_STUDENT_ACCESS_CODE,
                "session_uuid": "some-uuid",
                "allow": True,
            }
        )


def test_simple_command_data_rejects_set_exam_session_permission_command():
    with pytest.raises(pydantic.ValidationError):
        ktp_controller.messages.SimpleCommandData.model_validate(
            {
                "command": (
                    ktp_controller.messages.Command.SET_EXAM_SESSION_PERMISSION_TO_USE_BROWSERS
                ),
            }
        )


def test_set_exam_session_permission_to_use_browsers_command_data_requires_payload():
    with pytest.raises(pydantic.ValidationError):
        ktp_controller.messages.SetExamSessionPermissionToUseBrowsersCommandData.model_validate(
            {
                "command": (
                    ktp_controller.messages.Command.SET_EXAM_SESSION_PERMISSION_TO_USE_BROWSERS
                ),
            }
        )


def test_command_data_adapter_discriminates_simple_command():
    command_data = ktp_controller.messages.CommandDataAdapter.validate_python(
        {"command": ktp_controller.messages.Command.CHANGE_STUDENT_ACCESS_CODE}
    )

    assert isinstance(command_data, ktp_controller.messages.SimpleCommandData)


def test_command_data_adapter_discriminates_set_exam_session_permission_command():
    command_data = ktp_controller.messages.CommandDataAdapter.validate_python(
        {
            "command": (
                ktp_controller.messages.Command.SET_EXAM_SESSION_PERMISSION_TO_USE_BROWSERS
            ),
            "session_uuid": "some-uuid",
            "student_uuid": "some-student-uuid",
            "allow": True,
        }
    )

    assert isinstance(
        command_data,
        ktp_controller.messages.SetExamSessionPermissionToUseBrowsersCommandData,
    )
    assert command_data.session_uuid == "some-uuid"
    assert command_data.student_uuid == "some-student-uuid"
    assert command_data.allow is True


def test_set_exam_session_permission_to_use_browsers_command_data_requires_student_uuid():
    with pytest.raises(pydantic.ValidationError):
        ktp_controller.messages.SetExamSessionPermissionToUseBrowsersCommandData.model_validate(
            {
                "command": (
                    ktp_controller.messages.Command.SET_EXAM_SESSION_PERMISSION_TO_USE_BROWSERS
                ),
                "session_uuid": "some-uuid",
                "allow": True,
            }
        )


def test_command_data_adapter_rejects_unknown_command():
    with pytest.raises(pydantic.ValidationError):
        ktp_controller.messages.CommandDataAdapter.validate_python(
            {"command": "not_a_real_command"}
        )


def test_simple_command_data_rejects_allow_audio_replay_command():
    with pytest.raises(pydantic.ValidationError):
        ktp_controller.messages.SimpleCommandData.model_validate(
            {"command": ktp_controller.messages.Command.ALLOW_AUDIO_REPLAY}
        )


def test_allow_audio_replay_command_data_requires_student_uuid():
    with pytest.raises(pydantic.ValidationError):
        ktp_controller.messages.AllowAudioReplayCommandData.model_validate(
            {"command": ktp_controller.messages.Command.ALLOW_AUDIO_REPLAY}
        )


def test_command_data_adapter_discriminates_allow_audio_replay_command():
    command_data = ktp_controller.messages.CommandDataAdapter.validate_python(
        {
            "command": ktp_controller.messages.Command.ALLOW_AUDIO_REPLAY,
            "student_uuid": "some-student-uuid",
        }
    )

    assert isinstance(command_data, ktp_controller.messages.AllowAudioReplayCommandData)
    assert command_data.student_uuid == "some-student-uuid"


def test_simple_command_data_rejects_end_student_exam_command():
    with pytest.raises(pydantic.ValidationError):
        ktp_controller.messages.SimpleCommandData.model_validate(
            {"command": ktp_controller.messages.Command.END_STUDENT_EXAM}
        )


def test_end_student_exam_command_data_requires_payload():
    with pytest.raises(pydantic.ValidationError):
        ktp_controller.messages.EndStudentExamCommandData.model_validate(
            {"command": ktp_controller.messages.Command.END_STUDENT_EXAM}
        )


def test_end_student_exam_command_data_requires_student_uuid():
    with pytest.raises(pydantic.ValidationError):
        ktp_controller.messages.EndStudentExamCommandData.model_validate(
            {
                "command": ktp_controller.messages.Command.END_STUDENT_EXAM,
                "session_uuid": "some-uuid",
            }
        )


def test_command_data_adapter_discriminates_end_student_exam_command():
    command_data = ktp_controller.messages.CommandDataAdapter.validate_python(
        {
            "command": ktp_controller.messages.Command.END_STUDENT_EXAM,
            "session_uuid": "some-uuid",
            "student_uuid": "some-student-uuid",
        }
    )

    assert isinstance(command_data, ktp_controller.messages.EndStudentExamCommandData)
    assert command_data.session_uuid == "some-uuid"
    assert command_data.student_uuid == "some-student-uuid"
