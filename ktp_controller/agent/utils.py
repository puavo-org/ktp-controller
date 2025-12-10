# Standard library imports
import logging
import uuid

# Third-party imports

# Internal imports
import ktp_controller.messages
import ktp_controller.redis

# Relative imports

__all__ = [
    "PUBSUB_CHANNEL",
    "send_command",
]


_LOGGER = logging.getLogger(__file__)

PUBSUB_CHANNEL = f"ktp-controller__agent_messages__{ str(uuid.uuid4()) }"


async def send_command(command_data: ktp_controller.messages.CommandData) -> str:
    command_message = ktp_controller.messages.CommandMessage(data=command_data)
    return await ktp_controller.redis.pubsub_send(command_message, PUBSUB_CHANNEL)
