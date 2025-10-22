# Standard library imports
import enum

# Third-party imports

# Internal imports
import ktp_controller.pydantic

__all__ = [
    "AddAgentTaskResponseStatus",
    "AgentTask",
    "AgentTaskName",
    "AddAgentTaskResponse",
]


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


class AgentTask(ktp_controller.pydantic.BaseModel):
    name: AgentTaskName


class AddAgentTaskResponse(ktp_controller.pydantic.BaseModel):
    status: AddAgentTaskResponseStatus
    agent_task: AgentTask
