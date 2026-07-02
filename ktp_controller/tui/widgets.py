import collections
import datetime
import itertools
import logging
import typing

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Center, Container, Grid, Horizontal, Middle, Vertical
from textual.css.query import DOMQuery
from textual.widget import Widget
from textual.widgets import Button, DataTable, Label

import ktp_controller.schemas
import ktp_controller.utils

_LOGGER = logging.getLogger(__name__)


def _load_average_str(load_average: dict[str, float]) -> str:
    return " ".join(
        f"{key}: {round(load_average[key], 2)}" for key in ("1min", "5min", "15min")
    )


def _timestamp_str(dt: datetime.datetime) -> str:
    ago_str = ktp_controller.utils.relatimestr(dt)

    return f"{dt.astimezone().strftime('%Y-%m-%d %H:%M:%S')} ({ago_str})"


def _maybe_round(v: float | int, ndigits: int = 1) -> float | int:
    """
    >>> _maybe_round(3)
    3
    >>> _maybe_round(-3.0)
    -3
    >>> _maybe_round(3.12)
    3.1
    >>> _maybe_round(3.129, ndigits=2)
    3.13
    >>> _maybe_round(-0.01)
    -0.0
    """
    if isinstance(v, int):
        return v

    if v.is_integer():
        return int(v)

    return round(v, ndigits)


def _file_size_str(byte_count: int) -> str:
    """
    >>> _file_size_str(-20)
    Traceback (most recent call last):
    ...
    ValueError: byte_count cannot be negative

    >>> _file_size_str(0)
    '0 B'

    >>> _file_size_str(234)
    '234 B'

    >>> _file_size_str(1234)
    '1.2 KiB'

    >>> _file_size_str(1024 * 1024)
    '1 MiB'

    >>> _file_size_str(12345678977777777)
    '11228.3 TiB'
    """

    if byte_count < 0:
        raise ValueError("byte_count cannot be negative")

    for exp, unit in enumerate(["B", "KiB", "MiB", "GiB", "TiB"]):
        value = byte_count / (1024**exp)
        if value < 1024:
            return f"{_maybe_round(value)} {unit}"

    return f"{_maybe_round(value)} {unit}"


def _seconds_to_dhms_str(uptime_secs: float | int) -> str:
    """
    >>> _seconds_to_dhms_str(67)
    '1m 7s'
    >>> _seconds_to_dhms_str(3617.67)
    '1h 0m 18s'
    >>> _seconds_to_dhms_str(-53)
    Traceback (most recent call last):
    ...
    ValueError: uptime_secs cannot be negative
    """
    if uptime_secs < 0:
        raise ValueError("uptime_secs cannot be negative")

    if uptime_secs < 60:
        return f"{round(uptime_secs)}s"

    uptime_mins, uptime_secs = divmod(uptime_secs, 60)
    if uptime_mins < 60:
        return f"{round(uptime_mins)}m {round(uptime_secs)}s"

    uptime_hours, uptime_mins = divmod(uptime_mins, 60)
    if uptime_hours < 24:
        return f"{round(uptime_hours)}h {round(uptime_mins)}m {round(uptime_secs)}s"

    uptime_days, uptime_hours = divmod(uptime_hours, 24)
    return f"{round(uptime_days)}d {round(uptime_hours)}h {round(uptime_mins)}m {round(uptime_secs)}s"


def _get_text(value: typing.Any) -> Text:
    if isinstance(value, Text):
        return value
    return Text(str(value), justify="center")


def _get_by_path(obj: typing.Any, path: str) -> typing.Any:
    """Traverse dots for attributes, integers for list indices."""
    for part in path.split("."):
        obj = obj[int(part)] if part.isdigit() else getattr(obj, part)
        if obj is None:
            break
    return obj


class _StatusReportWidget(Widget):
    DEFAULT_CSS = """
    _StatusReportWidget {
        height: auto;
        layers: base overlay;
    }

    #no_data_container {
        border: solid $primary;
        color: $text-muted;
        layer: overlay;
        display: block;
    }

    #data_container {
        border: solid $primary;
        height: 1fr;
        layer: base;
        display: none;
    }

    _StatusReportWidget.has-data #no_data_container {
        display: none;
    }

    _StatusReportWidget.has-data #data_container {
        display: block;
    }

    #fields_container {
        height: auto;
    }

    #buttons {
        width: auto;
        border-left: solid $primary;
        overflow: auto;
    }

    #fields {
        grid-size: 4;
        grid-columns: auto 1fr;
        grid-rows: 1;
        grid-gutter: 0 1;
        padding: 1;
        height: auto;
    }

    Label.key {
        text-align: left;
        color: $accent;
        width: 100%;
    }

    Label.value {
        text-style: bold;
    }

    DataTable {
        margin: 1;
    }
    """

    _LABEL_ID_PREFIX = "Label-"
    _MANUAL_CONTROL_BUTTON_ID_PREFIX = "ManualControlButton-"

    def __init__(
        self,
        *,
        title: str,
        fields: tuple[list[tuple[str, str]], list[tuple[str, str]]],
        fieldfuncs: dict[str, typing.Callable[[typing.Any], str]] | None = None,
        manual_control_buttons: list[str] | None = None,
        data_table_items: str | None = None,
        data_table_columns: list[tuple[str, str]] | None = None,
        **kwargs: typing.Any,
    ) -> None:
        if fieldfuncs is None:
            fieldfuncs = collections.defaultdict(lambda v: str(v))  # type: ignore

        super().__init__(**kwargs)
        self.__title = title
        self.__fields = fields
        self.__fieldfuncs = fieldfuncs
        self.__manual_control_buttons = manual_control_buttons
        self.__data_table_items_path = data_table_items
        self.__data_table_columns = data_table_columns
        self._status_report: ktp_controller.schemas.StatusReport | None = None

    def compose(self) -> ComposeResult:
        with Container(id="data_container") as data_container:
            data_container.border_title = self.__title
            with Horizontal(id="fields_container"):
                with Grid(id="fields"):
                    for label, path in itertools.chain(
                        *itertools.zip_longest(*self.__fields, fillvalue=(None, None))
                    ):
                        if label is None or path is None:
                            yield Label("", classes="key")
                            yield Label("", classes="value")
                        else:
                            if "-" in path:
                                raise ValueError("path cannot have hyphens")
                            yield Label(label, classes="key")
                            yield Label(
                                "-",
                                id=f"{self._LABEL_ID_PREFIX}{path.replace('.', '-')}",
                                classes="value",
                            )
                if self.__manual_control_buttons:
                    with Vertical(id="buttons"):
                        for label in self.__manual_control_buttons:
                            yield Button(
                                label,
                                id=f"{self._MANUAL_CONTROL_BUTTON_ID_PREFIX}{label}",
                                classes="manual_control",
                                disabled=True,
                            )
            if self.__data_table_columns is not None:
                with Container(id="data_table_container"):
                    yield DataTable()

        with Center(id="no_data_container") as no_data_container:
            no_data_container.border_title = self.__title
            with Middle():
                yield Label(id="no_data_label")

    def on_mount(self) -> None:
        self.__refresh()

        if self.__data_table_columns is None:
            return

        table = self.query_exactly_one(DataTable)
        table.cursor_type = "none"
        table.zebra_stripes = True
        table.header_height = 2
        column_titles = [_get_text(v[0]) for v in self.__data_table_columns]
        table.add_columns(*column_titles)
        table.allow_focus = lambda: False  # type: ignore

    def set_status_report(
        self, status_report: ktp_controller.schemas.StatusReport | None
    ) -> None:
        self._status_report = status_report
        self.__refresh()

    def _get_no_data_info(self) -> tuple[bool, str]:
        return (
            self._status_report is not None,
            "[b i $error]ERROR: STATUS REPORT NOT AVAILABLE[/b i $error]",
        )

    def _get_row_values(self, item: typing.Any) -> list[typing.Any]:
        return []

    def __refresh(self) -> None:
        has_data, no_data_message = self._get_no_data_info()
        self.set_class(has_data, "has-data")
        typing.cast(Label, self.query_exactly_one("#no_data_label")).update(
            no_data_message
        )

        for buttons in self.query(".manual_control"):
            buttons.disabled = (
                self._status_report is None
                or self._status_report.ktp_controller.is_auto_control_enabled
            )

        for label in typing.cast(DOMQuery[Label], self.query("Label.value")):
            if label.id is None or not label.id.startswith(self._LABEL_ID_PREFIX):
                continue
            key = label.id[len(self._LABEL_ID_PREFIX) :].replace("-", ".")
            try:
                value = _get_by_path(self._status_report, key)
            except (AttributeError, IndexError):
                value = "[b i $error]ERROR: VALUE NOT AVAILABLE[/b i $error]"
            else:
                value = "-" if value is None else self.__fieldfuncs.get(key, str)(value)
            label.update(value)

        if self.__data_table_columns is not None:
            data_table = self.query_exactly_one(DataTable)
            data_table.clear()

            if self.__data_table_items_path is not None:
                try:
                    items = (
                        _get_by_path(self._status_report, self.__data_table_items_path)
                        or []
                    )
                except (AttributeError, IndexError):
                    items = []

                if len(items) == 0:
                    rows = [[_get_text("-")] * len(data_table.columns)]
                else:
                    rows = [
                        [_get_text(v) for v in self._get_row_values(item)]
                        for item in items
                    ]

                for row in rows:
                    data_table.add_row(*row)


class KTPControllerInfoWidget(_StatusReportWidget):
    def __init__(self, **kwargs: typing.Any) -> None:
        super().__init__(
            title="KTP Controller info",
            fields=(
                [
                    ("Version", "ktp_controller.version"),
                ],
                [
                    ("Started at", "ktp_controller.started_at"),
                ],
            ),
            fieldfuncs={
                "ktp_controller.started_at": _timestamp_str,
            },
            **kwargs,
        )


class HostInfoWidget(_StatusReportWidget):
    def __init__(self, **kwargs: typing.Any) -> None:
        super().__init__(
            title="Host info",
            fields=(
                [
                    ("Release", "os.release"),
                ],
                [
                    ("Uptime", "os.stats.uptime"),
                    ("Load average", "os.stats.load_average"),
                ],
            ),
            fieldfuncs={
                "os.stats.uptime": _seconds_to_dhms_str,
                "os.stats.load_average": _load_average_str,
            },
            **kwargs,
        )


class Abitti2ServerInfoWidget(_StatusReportWidget):
    def __init__(self, **kwargs: typing.Any) -> None:
        super().__init__(
            title="Abitti2 server info",
            fields=(
                [
                    ("Domain", "abitti2.domain"),
                    ("Version", "abitti2.version"),
                ],
                [
                    ("Student access code", "abitti2.student_access_code"),
                    ("Supervisor passphrase", "abitti2.supervisor_passphrase"),
                ],
            ),
            data_table_items="abitti2.stats.exams",
            data_table_columns=[
                ("Exam title", "title"),
                ("Active\nstudents", "active_students_count"),
                ("Finished\nstudents", "finished_students_count"),
                ("Flagged\nstudents", "flagged_students_count"),
            ],
            **kwargs,
        )

    def _get_row_values(self, item: typing.Any) -> list[typing.Any]:
        total_students = (
            item.active_students_count
            + item.finished_students_count
            + item.flagged_students_count
        )
        return [
            item.title,
            f"{item.active_students_count}/{total_students}",
            f"{item.finished_students_count}/{total_students}",
            f"{item.flagged_students_count}/{total_students}",
        ]


class CurrentExamPackageWidget(_StatusReportWidget):
    def __init__(self, **kwargs: typing.Any) -> None:
        super().__init__(
            title="Current exam package",
            fields=(
                [
                    ("UUID", "ktp_controller.current_exam_package.uuid"),
                    (
                        "Scheduled to start at",
                        "ktp_controller.current_exam_package.scheduled_start_time",
                    ),
                    (
                        "Scheduled to end at",
                        "ktp_controller.current_exam_package.scheduled_end_time",
                    ),
                    ("File size", "ktp_controller.current_exam_package.file_size"),
                    ("State", "ktp_controller.current_exam_package.state"),
                ],
                [
                    ("Prepared at", "ktp_controller.current_exam_package.prepared_at"),
                    ("Started at", "ktp_controller.current_exam_package.started_at"),
                    ("Ended at", "ktp_controller.current_exam_package.ended_at"),
                    ("Archived at", "ktp_controller.current_exam_package.archived_at"),
                ],
            ),
            # manual_control_buttons=[
            #     "Prepare",
            #     "Start",
            #     "Stop",
            #     "Archive",
            # ],
            fieldfuncs={
                "ktp_controller.current_exam_package.scheduled_start_time": _timestamp_str,
                "ktp_controller.current_exam_package.scheduled_end_time": _timestamp_str,
                "ktp_controller.current_exam_package.prepared_at": _timestamp_str,
                "ktp_controller.current_exam_package.started_at": _timestamp_str,
                "ktp_controller.current_exam_package.ended_at": _timestamp_str,
                "ktp_controller.current_exam_package.archived_at": _timestamp_str,
                "ktp_controller.current_exam_package.file_size": _file_size_str,
            },
            **kwargs,
        )

    def _get_no_data_info(self) -> tuple[bool, str]:
        has_data, no_data_message = super()._get_no_data_info()
        if not has_data:
            return has_data, no_data_message

        return (
            self._status_report is not None
            and self._status_report.ktp_controller.current_exam_package is not None,
            "There are no currently scheduled exam packages.",
        )


class NextExamPackageWidget(_StatusReportWidget):
    def __init__(self, **kwargs: typing.Any) -> None:
        super().__init__(
            title="Next exam package",
            fields=(
                [
                    ("UUID", "ktp_controller.next_exam_packages.0.uuid"),
                    (
                        "Scheduled to start at",
                        "ktp_controller.next_exam_packages.0.scheduled_start_time",
                    ),
                    (
                        "Scheduled to end at",
                        "ktp_controller.next_exam_packages.0.scheduled_end_time",
                    ),
                    (
                        "Estimated file size",
                        "ktp_controller.next_exam_packages.0.estimated_file_size",
                    ),
                ],
                [],
            ),
            fieldfuncs={
                "ktp_controller.next_exam_packages.0.scheduled_start_time": _timestamp_str,
                "ktp_controller.next_exam_packages.0.scheduled_end_time": _timestamp_str,
                "ktp_controller.next_exam_packages.0.estimated_file_size": _file_size_str,
            },
            **kwargs,
        )

    def _get_no_data_info(self) -> tuple[bool, str]:
        has_data, no_data_message = super()._get_no_data_info()
        if not has_data:
            return has_data, no_data_message

        if (
            self._status_report is None
            or self._status_report.ktp_controller.next_exam_packages is None
        ):
            return (
                False,
                "[b i $error]ERROR: LIST OF UPCOMING EXAM PACKAGES NOT AVAILABLE[/b i $error]",
            )

        return (
            len(self._status_report.ktp_controller.next_exam_packages) > 0,
            "There are no upcoming scheduled exam packages.",
        )
