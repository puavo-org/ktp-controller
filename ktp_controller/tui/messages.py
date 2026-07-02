# Standard library imports
import asyncio
import datetime
import logging

# Third-party imports
import websockets
from textual.app import App
from textual.message import Message as TextualMessage

# Internal imports
import ktp_controller.api.client
import ktp_controller.messages
import ktp_controller.schemas


class MsgCommand(TextualMessage):
    def __init__(self, command_message: ktp_controller.messages.CommandMessage) -> None:
        super().__init__()
        self.__command_message = command_message

    @property
    def command_uuid(self) -> str:
        return str(self.__command_message.uuid)

    def __str__(self) -> str:
        return f"'{self.__command_message.data.command}' command {self.command_uuid}"


class MsgCommandResult(TextualMessage):
    def __init__(
        self, command_result_message: ktp_controller.messages.CommandResultMessage
    ) -> None:
        super().__init__()
        self.__command_result_message = command_result_message

    @property
    def command_uuid(self) -> str:
        return str(self.__command_result_message.data.command_uuid)

    @property
    def __command_status(self) -> ktp_controller.messages.CommandStatus:
        return self.__command_result_message.data.command_status

    @property
    def __error_message(self) -> str | None:
        return self.__command_result_message.data.error_message

    def __str__(self) -> str:
        details = "" if self.__command_status.is_ok else f": {self.__error_message}"
        return (
            f"result of command {self.command_uuid}: {self.__command_status}{details}"
        )


class MsgLogRecord(TextualMessage):
    def __init__(self, record: logging.LogRecord) -> None:
        super().__init__()
        self.record = record

    def __str__(self) -> str:
        ts = (
            datetime.datetime.fromtimestamp(self.record.created)
            .astimezone()
            .strftime("%H:%M:%S.%f")
        )
        return f"{ts} {self.record.levelname} {self.record.name}: {self.record.getMessage()}"


class MsgStatusReport(TextualMessage):
    def __init__(
        self, status_report_message: ktp_controller.messages.StatusReportMessage
    ) -> None:
        super().__init__()
        self.status_report = status_report_message.data.status_report


class MsgConnected(TextualMessage):
    def __init__(
        self,
    ) -> None:
        super().__init__()


class MsgDisconnected(TextualMessage):
    def __init__(
        self,
        *,
        reconnect_delay: int = 0,
        error_message: str | None = None,
    ) -> None:
        super().__init__()
        self.reconnect_delay = reconnect_delay
        self.error_message = error_message


async def message_loop(app: App) -> None:  # type: ignore
    reconnect_delay = 1
    max_reconnect_delay = 16

    while True:
        try:
            async with websockets.connect(
                ktp_controller.api.client.get_ui_websock_url()
            ) as websock:
                reconnect_delay = 1
                app.post_message(MsgConnected())
                async for data in websock:
                    msg_dict = ktp_controller.utils.json_loads_dict(data)
                    kind = msg_dict.get("kind")
                    if kind == ktp_controller.messages.MessageKind.STATUS_REPORT:
                        status_report_message = (
                            ktp_controller.messages.StatusReportMessage.model_validate(
                                msg_dict
                            )
                        )
                        app.post_message(MsgStatusReport(status_report_message))
                    elif kind == ktp_controller.messages.MessageKind.COMMAND:
                        command_message = (
                            ktp_controller.messages.CommandMessage.model_validate(
                                msg_dict
                            )
                        )
                        app.post_message(MsgCommand(command_message))
                    elif kind == ktp_controller.messages.MessageKind.COMMAND_RESULT:
                        command_result_message = (
                            ktp_controller.messages.CommandResultMessage.model_validate(
                                msg_dict
                            )
                        )
                        app.post_message(MsgCommandResult(command_result_message))
        except Exception as exc:
            app.post_message(
                MsgDisconnected(
                    reconnect_delay=reconnect_delay,
                    error_message=str(exc),
                )
            )
            await asyncio.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)
