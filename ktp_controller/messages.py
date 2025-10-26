# Standard library imports
import enum
import typing
import uuid

# Third-party imports
import pydantic

# Internal imports
import ktp_controller.pydantic

# Relative imports


__all__ = [
    # Enums:
    "Command",
    "CommandStatus",
    "MessageKind",
    # Types:
    "CommandData",
    "CommandResultData",
    "PongData",
    "StatusReportData",
    "Data",
    "CommandMessage",
    "CommandResultMessage",
    "PingMessage",
    "PongMessage",
    "StatusReportMessage",
    "Data",
    "Message",
]


# Enums:


class Command(str, enum.Enum):
    ENABLE_AUTO_CONTROL = "enable_auto_control"
    DISABLE_AUTO_CONTROL = "disable_auto_control"

    def __str__(self) -> str:
        return self.value


class CommandStatus(str, enum.Enum):
    OK = "ok"
    OK_NO_CHANGE = "ok_no_change"
    ERROR = "error"

    def __str__(self) -> str:
        return self.value

    @property
    def is_ok(self) -> bool:
        return self.value == "ok" or self.value.startswith("ok_")


class MessageKind(str, enum.Enum):
    PING = "ping"
    PONG = "pong"
    COMMAND = "command"
    COMMAND_RESULT = "command_result"
    STATUS_REPORT = "status_report"

    def __str__(self) -> str:
        return self.value


# Types:


class CommandData(ktp_controller.pydantic.BaseModel):
    command: Command


class CommandResultData(ktp_controller.pydantic.BaseModel):
    command_uuid: pydantic.UUID4
    command_status: CommandStatus
    error_message: str | None = None


class PongData(ktp_controller.pydantic.BaseModel):
    ping_uuid: pydantic.UUID4


class StatusReportData(ktp_controller.pydantic.BaseModel):
    is_auto_control_enabled: pydantic.StrictBool


Data = typing.Union[CommandData, CommandResultData, PongData, StatusReportData, None]


class _MessageBase(ktp_controller.pydantic.BaseModel):
    uuid: pydantic.UUID4 = pydantic.Field(default_factory=lambda: str(uuid.uuid4()))
    kind: MessageKind
    data: Data


class CommandMessage(_MessageBase):
    kind: typing.Literal[MessageKind.COMMAND] = MessageKind.COMMAND
    data: CommandData


class CommandResultMessage(_MessageBase):
    kind: typing.Literal[MessageKind.COMMAND_RESULT] = MessageKind.COMMAND_RESULT
    data: CommandResultData


class PingMessage(_MessageBase):
    kind: typing.Literal[MessageKind.PING] = MessageKind.PING
    data: None = None


class PongMessage(_MessageBase):
    kind: typing.Literal[MessageKind.PONG] = MessageKind.PONG
    data: PongData


class StatusReportMessage(_MessageBase):
    kind: typing.Literal[MessageKind.STATUS_REPORT] = MessageKind.STATUS_REPORT
    data: StatusReportData


Message = typing.Union[
    CommandMessage, CommandResultMessage, PingMessage, PongMessage, StatusReportMessage
]
