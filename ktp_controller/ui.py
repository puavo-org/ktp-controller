# Standard library imports
import typing
import uuid

# Third-party imports
# Internal imports
import ktp_controller.messages
import ktp_controller.redis
import ktp_controller.schemas

# Relative imports


__all__ = [
    "PUBSUB_CHANNEL",
    "forward_command_message",
    "forward_command_result_message",
    "send_status_report",
]


PUBSUB_CHANNEL = f"ktp-controller__ui_messages__{uuid.uuid4()!s}"


async def forward_command_message(
    command_message: ktp_controller.messages.CommandMessage,
) -> str:
    return await ktp_controller.redis.pubsub_send(command_message, PUBSUB_CHANNEL)


async def forward_command_result_message(
    command_result_message: ktp_controller.messages.CommandResultMessage,
) -> str:
    return await ktp_controller.redis.pubsub_send(
        command_result_message, PUBSUB_CHANNEL
    )


async def send_status_report(status_report_dict: dict[str, typing.Any]) -> str:
    status_report = ktp_controller.schemas.StatusReport.model_validate(
        status_report_dict
    )
    status_report_data = ktp_controller.messages.StatusReportData(
        status_report=status_report
    )
    status_report_message = ktp_controller.messages.StatusReportMessage(
        data=status_report_data
    )

    return await ktp_controller.redis.pubsub_send(status_report_message, PUBSUB_CHANNEL)
