# Standard library imports
import enum
import typing

# Third-party imports
import pydantic

__all__ = [
    "AgentTask",
    "AgentTaskName",
]


StrictPositiveIntT = typing.TypeVar(
    "StrictPositiveIntT", pydantic.StrictInt, pydantic.PositiveInt
)
StrictPositiveInt: typing.TypeAlias = StrictPositiveIntT


class AddAgentTaskResponseStatus(str, enum.Enum):
    STARTED = "started"
    DEFERRED_UNTIL_AGENT_IS_CONTACTED = "deferred_until_agent_is_contacted"

    def __str__(self) -> str:
        return self.value


class AgentTaskName(str, enum.Enum):
    CHANGE_KEYCODES = "change_keycodes"
    REFRESH_EXAMS = "refresh_exams"

    def __str__(self) -> str:
        return self.value


class AgentTask(pydantic.BaseModel):
    name: AgentTaskName


class AddAgentTaskResponse(pydantic.BaseModel):
    status: AddAgentTaskResponseStatus
    agent_task: AgentTask
