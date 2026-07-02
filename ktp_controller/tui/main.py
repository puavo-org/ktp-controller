# Standard library imports
import asyncio
import logging
import threading
import typing

# Third-party imports
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.reactive import reactive
from textual.widgets import (
    Button,
    Footer,
    Header,
    Label,
    RichLog,
    Rule,
    TabbedContent,
    TabPane,
)

import ktp_controller.api.client
import ktp_controller.messages
import ktp_controller.utils

from .messages import (
    MsgCommandResult,
    MsgConnected,
    MsgDisconnected,
    MsgLogRecord,
    MsgStatusReport,
    message_loop,
)
from .screens import DisableAutoControlQuestion
from .widgets import (
    Abitti2ServerInfoWidget,
    CurrentExamPackageWidget,
    HostInfoWidget,
    KTPControllerInfoWidget,
    NextExamPackageWidget,
)

_LOGGER = logging.getLogger(__name__)


class _TuiLogHandler(logging.Handler):
    def __init__(self, app: "KtpTuiApp") -> None:
        super().__init__()
        self._app = app

    def emit(self, record: logging.LogRecord) -> None:
        self._app.post_message(MsgLogRecord(record))


class KtpTuiApp(App[None]):
    TITLE = "KTP Controller Client"
    BINDINGS: typing.ClassVar[
        list[Binding | tuple[str, str] | tuple[str, str, str]]
    ] = [
        Binding("q", "bye", "Quit"),
        Binding("b", "noop", show=False),
        Binding("t", "toggle_auto_control", "Toggle auto control"),
        Binding("1", "show_tab(1)", "Scheduling"),
        Binding("2", "show_tab(2)", "Abitti2"),
        Binding("3", "show_tab(3)", "Statistics"),
        Binding("4", "show_tab(4)", "Client log"),
    ]

    CSS = """
    Screen {
        align: center middle;
    }

    .status-container {
       border: solid $primary;
       width: 100%;
       height: 3;
    }

    .status {
      height: 1;
      content-align: center middle;
      width: auto;
    }

    #RichLog-client-log {
      padding: 1;
      border: solid $primary;
    }
    """

    is_auto_control_enabled: reactive[bool | None] = reactive(None, bindings=True)

    def __init__(self) -> None:
        super().__init__()
        self._pending_command_uuid: str | None = None
        self._pending_command_uuid_lock = asyncio.Lock()
        self._ws_task: asyncio.Task[None] | None = None
        self._log_handler = _TuiLogHandler(self)
        self._saved_root_log_handlers: list[logging.Handler] = []

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(), TabbedContent():
            with TabPane("1 - Scheduling"):
                with Container():
                    yield CurrentExamPackageWidget()
                with Container():
                    yield NextExamPackageWidget()
            with TabPane("2 - Abitti2"):
                yield Abitti2ServerInfoWidget()
            with TabPane("3 - Statistics"):
                with Container():
                    yield KTPControllerInfoWidget()
                with Container():
                    yield HostInfoWidget()
            with TabPane("4 - Client log"):
                richlog = RichLog(
                    id="RichLog-client-log",
                    highlight=True,
                    markup=False,
                    wrap=True,
                    max_lines=1000,
                    auto_scroll=False,
                )
                richlog.allow_focus = lambda: False  # type: ignore
                yield richlog
        yield Horizontal(
            Rule(orientation="vertical"),
            Label(
                "Client is [bold red]DISCONNECTED[/]",
                id="Label-connection-status",
                classes="status",
            ),
            Rule(orientation="vertical"),
            Label(
                "Auto control is [bold red]UNKNOWN[/] ",
                id="Label-auto-control-status",
                classes="status",
            ),
            classes="status-container",
        )
        yield Footer()

    # BEGIN Textual events

    def on_button_pressed(self, event: Button.Pressed) -> None:
        pass

    def on_mount(self) -> None:
        root_logger = logging.getLogger()
        self._saved_root_log_handlers = root_logger.handlers[:]
        root_logger.handlers = [self._log_handler]
        threading.Thread(target=self._start_message_loop, daemon=True).start()
        _LOGGER.info("Started.")

    def on_unmount(self) -> None:
        root_logger = logging.getLogger()
        root_logger.handlers = self._saved_root_log_handlers

    def on_msg_log_record(self, message: MsgLogRecord) -> None:
        richlog_client_log = self.query_one("#RichLog-client-log", RichLog)
        richlog_client_log.write(str(message))

    def on_msg_status_report(self, message: MsgStatusReport) -> None:
        _LOGGER.info("Received status report.")
        self.is_auto_control_enabled = (
            message.status_report.ktp_controller.is_auto_control_enabled
        )
        self.query_exactly_one(CurrentExamPackageWidget).set_status_report(
            message.status_report
        )
        self.query_exactly_one(NextExamPackageWidget).set_status_report(
            message.status_report
        )
        self.query_exactly_one(Abitti2ServerInfoWidget).set_status_report(
            message.status_report
        )
        self.query_exactly_one(KTPControllerInfoWidget).set_status_report(
            message.status_report
        )
        self.query_exactly_one(HostInfoWidget).set_status_report(message.status_report)

    def on_msg_command_result(self, message: MsgCommandResult) -> None:
        self._handle_command_result_in_the_background(message)

    def on_msg_connected(self, message: MsgConnected) -> None:
        _LOGGER.info("Connected to KTP Controller.")
        label_connection_status = self.query_one("#Label-connection-status", Label)
        label_connection_status.update(r"Client is [bold green]CONNECTED[/]   ")

    def on_msg_disconnected(self, message: MsgDisconnected) -> None:
        label_connection_status = self.query_one("#Label-connection-status", Label)
        label_connection_status.update(r"Client is [bold red]DISCONNECTED[/]")
        if message.error_message:
            _LOGGER.error("KTP Controller connection error: %s", message.error_message)
        _LOGGER.info(
            "Disconnected from KTP Controller. Reconnecting in %d seconds...",
            message.reconnect_delay,
        )
        self.is_auto_control_enabled = None
        self.query_exactly_one(CurrentExamPackageWidget).set_status_report(None)
        self.query_exactly_one(NextExamPackageWidget).set_status_report(None)
        self.query_exactly_one(Abitti2ServerInfoWidget).set_status_report(None)
        self.query_exactly_one(KTPControllerInfoWidget).set_status_report(None)
        self.query_exactly_one(HostInfoWidget).set_status_report(None)

    # END Textual events

    # BEGIN Textual actions

    def check_action(
        self, action: str, parameters: tuple[typing.Any, ...]
    ) -> bool | None:
        if action == "toggle_auto_control" and self.is_auto_control_enabled is None:
            return None  # None dims, False hides

        return True

    def action_noop(self) -> None:
        pass

    def action_show_tab(self, num: int) -> None:
        self.query_one(TabbedContent).active = f"tab-{num}"

    def action_bye(self) -> None:
        self.exit()

    @work
    async def action_toggle_auto_control(self) -> None:
        if self.is_auto_control_enabled is None:
            raise RuntimeError(
                "toggling should be disabled when is_auto_control_enabled is None"
            )
        if not self.is_auto_control_enabled:
            command = ktp_controller.messages.Command.ENABLE_AUTO_CONTROL
        else:
            if not await self.push_screen_wait(DisableAutoControlQuestion()):
                return
            command = ktp_controller.messages.Command.DISABLE_AUTO_CONTROL
        self._send_async_command_in_the_background(command)

    # END Textual actions

    def watch_is_auto_control_enabled(
        self, was_enabled: bool | None, is_enabled: bool | None
    ) -> None:
        if was_enabled == is_enabled:
            return

        label_auto_control_status = self.query_one("#Label-auto-control-status", Label)

        if is_enabled is None:
            _LOGGER.warning("Auto control is now unknown.")
            label_auto_control_status.update(r"Auto control is [bold red]UNKNOWN[/] ")
            return

        if not is_enabled:
            _LOGGER.warning("Auto control is now disabled.")
            label_auto_control_status.update(
                r"Auto control is [bold yellow]DISABLED[/]"
            )
            return

        _LOGGER.info("Auto control is now enabled.")
        label_auto_control_status.update(r"Auto control is [bold green]ENABLED[/] ")

    def _start_message_loop(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(message_loop(self))

    @work
    async def _handle_command_result_in_the_background(
        self, command_result: MsgCommandResult
    ) -> None:
        async with self._pending_command_uuid_lock:
            if command_result.command_uuid == self._pending_command_uuid:
                _LOGGER.info("Received %s", command_result)
                self._pending_command_uuid = None

    @work(exclusive=True)
    async def _send_async_command_in_the_background(
        self, command: ktp_controller.messages.Command
    ) -> None:
        _LOGGER.info("Sending command '%s''...", command)
        async with self._pending_command_uuid_lock:
            if self._pending_command_uuid is not None:
                _LOGGER.error(
                    "There is already a pending command %s", self._pending_command_uuid
                )
                return

            self._pending_command_uuid = await ktp_controller.api.client.async_command(
                command
            )
            _LOGGER.info(
                "Command '%s' is now pending with uuid %s.",
                command,
                self._pending_command_uuid,
            )


def run() -> int:
    app = KtpTuiApp()
    app.run()
    return 0
