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
            "allow": True,
        }
    )

    assert isinstance(
        command_data,
        ktp_controller.messages.SetExamSessionPermissionToUseBrowsersCommandData,
    )
    assert command_data.session_uuid == "some-uuid"
    assert command_data.allow is True


def test_command_data_adapter_rejects_unknown_command():
    with pytest.raises(pydantic.ValidationError):
        ktp_controller.messages.CommandDataAdapter.validate_python(
            {"command": "not_a_real_command"}
        )
