# Standard library imports
import typing

from textual import on

# Third-party imports
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Label,
)
from textual.widgets.button import ButtonVariant


class YesNoScreen(ModalScreen[bool]):
    CSS = """
    YesNoScreen {
      align: center middle; /* Centers the dialog box on the terminal screen */
      background: rgba(0, 0, 0, 0.5); /* Dim the background behind the modal */
    }

    #YesNoScreen-dialog {
      width: auto;
      height: auto;
      border: solid $accent;
      background: $surface;
      padding: 1 2;
      align: center middle;
    }

    #YesNoScreen-dialog Label {
      margin-bottom: 1;
    }

    #YesNoScreen-buttons {
      align: center middle;
      width: 100%;
      height: auto;
    }

    #YesNoScreen-buttons Button {
        margin: 0 1; /* Adds a space between the Yes and No buttons */
    }
    """

    def __init__(
        self,
        question: str,
        *,
        description: str | None = None,
        yes_variant: ButtonVariant = "default",
        no_variant: ButtonVariant = "default",
        default_focus: typing.Literal["yes", "no"] | None = None,
    ) -> None:
        self.__question = question
        self.__description = description
        self.__yes_variant = yes_variant
        self.__no_variant = no_variant
        self.__default_focus = default_focus
        super().__init__()

    def compose(self) -> ComposeResult:
        with Container(id="YesNoScreen-dialog"):
            if self.__description is not None:
                yield Label(self.__description)
            yield Label(self.__question)

            with Horizontal(id="YesNoScreen-buttons"):
                yield Button("Yes", id="yes", variant=self.__yes_variant)
                yield Button("No", id="no", variant=self.__no_variant)

    def on_mount(self) -> None:
        focus_widget = None
        if self.__default_focus == "yes":
            focus_widget = self.query_one("#yes", Button)
        elif self.__default_focus == "no":
            focus_widget = self.query_one("#no", Button)
        self.set_focus(focus_widget)

    @on(Button.Pressed, "#yes")
    def handle_yes(self) -> None:
        self.dismiss(True)

    @on(Button.Pressed, "#no")
    def handle_no(self) -> None:
        self.dismiss(False)


class DisableAutoControlQuestion(YesNoScreen):
    def __init__(self) -> None:
        super().__init__(
            "Do you really want to disable auto control?",
            description="""
Disabling auto control [b $accent]suspends[/b $accent] automatic management of Abitti2 server.

Most notably, [b $accent]following automatic procedures[/b $accent] will be suspended until auto control is manually re-enabled:

  - [b $accent]scheduled exam package management[/b $accent] (e.g. preparing, starting, stopping and archiving)
  - [b $accent]answer transfers to Exam-O-Matic[/b $accent]
""",
            yes_variant="warning",
            no_variant="success",
            default_focus="no",
        )
