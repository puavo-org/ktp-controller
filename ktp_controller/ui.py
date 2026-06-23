# Standard library imports
import uuid

import ktp_controller.messages

# Third-party imports
# Internal imports
import ktp_controller.redis

# Relative imports


__all__ = [
    # Constants:
    "PUBSUB_CHANNEL",
    # Utils:
    "forward_command_result_message",
    "send_status_report",
]


# Constants


PUBSUB_CHANNEL = f"ktp-controller__ui_messages__{uuid.uuid4()!s}"


# Utils:


async def forward_command_result_message(
    command_result_message: ktp_controller.messages.CommandResultMessage,
) -> str:
    return await ktp_controller.redis.pubsub_send(
        command_result_message, PUBSUB_CHANNEL
    )


async def forward_status_report_message(
    status_report_message: ktp_controller.messages.StatusReportMessage,
) -> str:
    return await ktp_controller.redis.pubsub_send(status_report_message, PUBSUB_CHANNEL)


async def send_status_report(
    status_repot_data: ktp_controller.messages.StatusReportData,
) -> str:
    status_report_message = ktp_controller.messages.StatusReportMessage(
        data=status_repot_data
    )
    return await ktp_controller.redis.pubsub_send(status_report_message, PUBSUB_CHANNEL)
