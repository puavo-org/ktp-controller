# Standard library imports
import enum
import logging
import os.path
import typing

# Third-party imports
import fastapi
import fastapi.responses
import fastapi.templating

# Internal imports
import ktp_controller.api.client
import ktp_controller.schemas
import ktp_controller.utils
import ktp_controller.wui.auth
import ktp_controller.wui.i18n
import ktp_controller.wui.schemas
import ktp_controller.wui.students
import ktp_controller.wui.utils

# Relative imports
from . import schemas

__all__ = [
    "router",
]

_LOGGER = logging.getLogger(__name__)

router = fastapi.APIRouter(tags=["htmx"])
_thisdir = os.path.dirname(__file__)
_templates = fastapi.templating.Jinja2Templates(
    directory=[
        os.path.join(_thisdir, "templates"),
        os.path.join(os.path.dirname(_thisdir), "templates"),
    ],
    context_processors=[ktp_controller.wui.i18n.template_context_processor],
)
# jinja2.select_autoescape()'s default extensions don't match our
# "*.html.j2" filenames, and {% extends %} must be the first top-level
# statement in a template, so it can't be wrapped in a per-file
# {% autoescape %} block like our non-inheriting templates are.
_templates.env.autoescape = True
_templates.env.add_extension("jinja2.ext.i18n")
_templates.env.install_null_translations(newstyle=True)  # type: ignore[attr-defined]
_templates.env.filters["localize_datetime"] = ktp_controller.wui.i18n.localize_datetime
_templates.env.filters["format_ddmmyy"] = ktp_controller.utils.format_ddmmyy
_templates.env.filters["extract"] = ktp_controller.wui.utils.extract_filter


async def _get_exams() -> list[schemas.Exam]:
    exams: list[schemas.Exam] = []
    abitti2_exams = await ktp_controller.abitti2.client.get_decrypted_exams()
    api_exams_by_external_id: dict[
        str, dict[str, typing.Any]
    ] = {}  # ktp_controller.api.client.get_current_exams()
    for abitti2_exam in sorted(abitti2_exams, key=lambda e: e["examTitle"]):
        external_id = abitti2_exam["examUuid"].lower()
        try:
            api_exam = api_exams_by_external_id[external_id]
        except KeyError:
            scheduled_start_time = None
            scheduled_end_time = None
        else:
            scheduled_start_time = api_exam["scheduled_start_time"]
            scheduled_end_time = api_exam["scheduled_end_time"]
        student_state_counts = ktp_controller.wui.schemas.StudentStateCounts()
        exams.append(
            schemas.Exam(
                title=abitti2_exam["examTitle"],
                external_id=external_id,
                student_state_counts=student_state_counts,
                started_at=abitti2_exam["startTime"],
                scheduled_start_time=scheduled_start_time,
                scheduled_end_time=scheduled_end_time,
            )
        )

    return exams


class _Order(enum.StrEnum):
    ASC = "asc"
    DESC = "desc"


class _StudentListItemSortableField(enum.StrEnum):
    NAME = "name"
    BIRTHDAY = "birthday"
    STATE = "state"
    LAST_CHANGED_AT = "last_changed_at"


def _group_student_list_items_by_exam_title(
    exams: list[schemas.Exam],
    student_list_items: list[ktp_controller.wui.schemas.StudentListItem],
) -> tuple[
    dict[str, list[ktp_controller.wui.schemas.StudentListItem]],
    list[ktp_controller.wui.schemas.StudentListItem],
]:
    ungrouped: list[ktp_controller.wui.schemas.StudentListItem] = []
    grouped: dict[str, list[ktp_controller.wui.schemas.StudentListItem]] = {}
    for exam in exams:
        grouped[exam.title] = []
    for student_list_item in student_list_items:
        if student_list_item.exam_title is None:
            ungrouped.append(student_list_item)
            continue
        try:
            grouped[student_list_item.exam_title].append(student_list_item)
        except KeyError:
            ungrouped.append(student_list_item)
    return dict(sorted(grouped.items())), ungrouped


@router.get("/", response_class=fastapi.responses.HTMLResponse)
@ktp_controller.wui.auth.require_permission("wui.invigilator.view")
async def _get_invigilator(
    request: fastapi.Request,
    sort_by: _StudentListItemSortableField = _StudentListItemSortableField.NAME,
    order: _Order = _Order.ASC,
    name_birthday_filter: str = "",
    session: ktp_controller.wui.auth.Session = fastapi.Depends(
        ktp_controller.wui.auth.get_current_session
    ),
) -> fastapi.responses.HTMLResponse:
    student_list_items = sorted(
        await ktp_controller.wui.students.get_student_list_items(),
        key=lambda x: getattr(x, sort_by),
        reverse=order == "desc",
    )

    exams = await _get_exams()

    can_reset_audio = any(item.last_audio is not None for item in student_list_items)

    student_state_counts = ktp_controller.wui.students.count_student_states(
        student_list_items
    )

    exam_titles_with_unfinished_students = {
        item.exam_title
        for item in student_list_items
        if item.exam_title is not None
        and item.state != ktp_controller.wui.schemas.StudentState.FINISHED
    }

    if name_birthday_filter:
        query = name_birthday_filter.lower()
        student_list_items = [
            item
            for item in student_list_items
            if query in item.name.lower() or query in item.birthday.isoformat()
        ]

    order_next = "desc" if order == "asc" else "asc"  # Next time the order is reversed

    grouped_student_list_items, ungrouped_student_list_items = (
        _group_student_list_items_by_exam_title(
            exams,
            student_list_items,
        )
    )

    grouped_student_state_counts = {
        exam_title: ktp_controller.wui.students.count_student_states(items)
        for exam_title, items in grouped_student_list_items.items()
    }
    ungrouped_student_state_counts = ktp_controller.wui.students.count_student_states(
        ungrouped_student_list_items
    )

    any_exam_group_open = bool(ungrouped_student_list_items) or any(
        exam_title in exam_titles_with_unfinished_students
        for exam_title in grouped_student_list_items
    )

    request.state.locale = session.locale
    _ = ktp_controller.wui.i18n.get_gettext(session.locale)

    column_labels = {
        _StudentListItemSortableField.NAME: _("Name"),
        _StudentListItemSortableField.BIRTHDAY: _("Birthday"),
        _StudentListItemSortableField.STATE: _("State"),
        _StudentListItemSortableField.LAST_CHANGED_AT: _("Last changed at"),
    }
    columns = (
        [
            (field.value, column_labels[field], True)
            for field in _StudentListItemSortableField
        ]
        + [(None, _("Allowed to use browsers"), False)]
        + ([(None, _("Last played audio"), False)] if can_reset_audio else [])
        + [(None, _("Action"), False)]
    )

    state_labels = ktp_controller.wui.students.get_student_state_labels(_)

    flag_labels = {
        ktp_controller.schemas.StudentFlag.DISCONNECTED: _("Disconnected"),
        ktp_controller.schemas.StudentFlag.IDLE: _("Idle"),
        ktp_controller.schemas.StudentFlag.WAITING_FOR_AUTH: _("Waiting for auth"),
        ktp_controller.schemas.StudentFlag.UNDEFINED_EXAM: _("Undefined exam"),
        ktp_controller.schemas.StudentFlag.UNKNOWN_ISSUE: _("Unknown issue"),
    }

    context = {
        "grouped_student_list_items": grouped_student_list_items,
        "ungrouped_student_list_items": ungrouped_student_list_items,
        "exam_titles_with_unfinished_students": exam_titles_with_unfinished_students,
        "any_exam_group_open": any_exam_group_open,
        "grouped_student_state_counts": grouped_student_state_counts,
        "ungrouped_student_state_counts": ungrouped_student_state_counts,
        "state_labels": state_labels,
        "flag_labels": flag_labels,
        "columns": columns,
        "sort_by": sort_by,
        "order_now": order,
        "order_next": order_next,
        "name_birthday_filter": name_birthday_filter,
        "user": session.username,
        "can_end_exam": "wui.actions.end-exam" in session.permissions,
        "can_set_browser_permission": (
            "wui.actions.set-exam-session-permission-to-use-browsers"
            in session.permissions
        ),
        "can_reset_audio": can_reset_audio,
        "can_allow_audio_replay": (
            "wui.actions.allow-audio-replay" in session.permissions
        ),
        "student_state_counts": student_state_counts,
    }

    # If the request comes from htmx, return only the table partial
    if request.headers.get("HX-Request"):
        return _templates.TemplateResponse(
            request, name="partials/student_list_groups.html.j2", context=context
        )

    # Otherwise return the full page
    return _templates.TemplateResponse(
        request, name="invigilator_index.html.j2", context=context
    )


@router.get("/student_access_code", response_class=fastapi.responses.HTMLResponse)
@ktp_controller.wui.auth.require_permission("wui.invigilator.view")
async def _get_student_access_code(
    request: fastapi.Request,
    session: ktp_controller.wui.auth.Session = fastapi.Depends(
        ktp_controller.wui.auth.get_current_session
    ),
) -> fastapi.responses.HTMLResponse:
    student_access_code_and_server_name = (
        await ktp_controller.api.client.get_student_access_code_and_server_name()
    )

    student_list_items = await ktp_controller.wui.students.get_student_list_items()
    student_state_counts = ktp_controller.wui.students.count_student_states(
        student_list_items
    )

    request.state.locale = session.locale
    _ = ktp_controller.wui.i18n.get_gettext(session.locale)

    context = {
        "student_access_code_and_server_name": student_access_code_and_server_name,
        "user": session.username,
        "can_change_access_code": (
            "wui.actions.change-student-access-code" in session.permissions
        ),
        "student_state_counts": student_state_counts,
        "state_labels": ktp_controller.wui.students.get_student_state_labels(_),
    }

    # If the request comes from htmx, return only the code display partial
    if request.headers.get("HX-Request"):
        return _templates.TemplateResponse(
            request,
            name="partials/student_access_code_display.html.j2",
            context=context,
        )

    # Otherwise return the full page
    return _templates.TemplateResponse(
        request, name="student_access_code.html.j2", context=context
    )


@router.websocket("/ws")
async def _invigilator_ws(websock: fastapi.WebSocket) -> None:
    try:
        # get_current_session() only reads .cookies, which fastapi.Request
        # and fastapi.WebSocket both implement identically.
        session = await ktp_controller.wui.auth.get_current_session(
            typing.cast(fastapi.Request, websock)
        )
    except ktp_controller.wui.auth.NotAuthenticatedError:
        await websock.close(code=4401)
        return
    if "wui.invigilator.view" not in session.permissions:
        await websock.close(code=4403)
        return

    # TODO: validate the Origin header against Host (CSWSH defense-in-depth),
    # reusing OriginCheckMiddleware's origin-parsing logic once extracted
    # into a shared helper. Skipped for now: consistent with the API's own
    # ui_websocket/agent_websocket endpoints, and the session cookie is
    # already SameSite=Lax.
    await websock.accept()
    registry: ktp_controller.wui.utils.BrowserSocketRegistry = (
        websock.app.state.invigilator_ws_registry
    )
    await registry.register(websock)
    try:
        while True:
            # Clients send nothing; this just detects disconnects.
            await websock.receive_text()
    except fastapi.WebSocketDisconnect:
        pass
    finally:
        await registry.unregister(websock)
