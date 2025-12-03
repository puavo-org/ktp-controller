# Standard library imports
import logging
import os.path
import uuid

# Third-party imports
import pydantic

# Internal imports
import ktp_controller.messages
import ktp_controller.pydantic
import ktp_controller.redis
import ktp_controller.utils

# Relative imports

__all__ = [
    # Constants:
    "PUBSUB_CHANNEL",
    # Types:
    "AgentState",
    # Utils:
    "send_command",
    "load_agent_state",
    "save_agent_state",
]


# Constants:
_LOGGER = logging.getLogger(__file__)

_AGENT_STATE_FILEPATH = os.path.expanduser(
    "~/.local/share/ktp-controller/agent-state.json"
)
PUBSUB_CHANNEL = f"ktp-controller__agent_messages__{ str(uuid.uuid4()) }"


# Types:


class AgentState(ktp_controller.pydantic.BaseModel):
    is_auto_control_enabled: pydantic.StrictBool = True


# Utils:


async def send_command(command_data: ktp_controller.messages.CommandData) -> str:
    command_message = ktp_controller.messages.CommandMessage(data=command_data)
    return await ktp_controller.redis.pubsub_send(command_message, PUBSUB_CHANNEL)


def load_agent_state() -> AgentState:
    _LOGGER.info("Loading agent state...")
    try:
        with open(_AGENT_STATE_FILEPATH, "r", encoding="ascii") as agent_state_file:
            agent_state = AgentState.model_validate_json(agent_state_file.read())
    except FileNotFoundError:
        _LOGGER.info(
            "Agent state file %r does not exist. Proceeding with an empty state.",
            _AGENT_STATE_FILEPATH,
        )
        agent_state = AgentState()
    except Exception:  # pylint: disable=broad-exception-caught
        _LOGGER.exception(
            "Failed to load the agent state. Proceeding with an empty state."
        )
        agent_state = AgentState()
    else:
        _LOGGER.info(
            "Loaded agent state successfully from '%r'.", _AGENT_STATE_FILEPATH
        )

    return agent_state


def save_agent_state(agent_state: AgentState) -> None:
    _LOGGER.info("Saving agent state...")
    dirpath = os.path.dirname(_AGENT_STATE_FILEPATH)
    try:
        os.makedirs(dirpath)
    except FileExistsError:
        _LOGGER.debug("Agent state file directory %r already exists.", dirpath)
    finally:
        with ktp_controller.utils.open_atomic_write(
            _AGENT_STATE_FILEPATH, encoding="ascii"
        ) as agent_state_file:
            agent_state_file.write(agent_state.model_dump_json(ensure_ascii=True))
        _LOGGER.info("Saved agent state successfully to %r.", _AGENT_STATE_FILEPATH)
