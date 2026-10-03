# Standard library imports
import datetime
import enum
import logging
import os.path
import typing
import uuid

# Third-party imports
import fastapi
import fastapi.responses
import fastapi.templating

# Internal imports
import ktp_controller.abitti2.client
import ktp_controller.abitti2.utils
import ktp_controller.api.client
import ktp_controller.messages
import ktp_controller.schemas
import ktp_controller.wui.auth
import ktp_controller.wui.i18n
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
    directory=os.path.join(_thisdir, "templates"),
    context_processors=[ktp_controller.wui.i18n.template_context_processor],
)
# jinja2.select_autoescape()'s default extensions don't match our
# "*.html.j2" filenames, and {% extends %} must be the first top-level
# statement in a template, so it can't be wrapped in a per-file
# {% autoescape %} block like our non-inheriting templates are.
_templates.env.autoescape = True
_templates.env.add_extension("jinja2.ext.i18n")
_templates.env.install_null_translations(newstyle=True)  # type: ignore[attr-defined]
_templates.env.filters["localize_date"] = ktp_controller.wui.i18n.localize_date
_templates.env.filters["localize_datetime"] = ktp_controller.wui.i18n.localize_datetime
_templates.env.filters["translate_labels"] = ktp_controller.wui.i18n.translate_labels


async def _get_student_list_items() -> list[schemas.StudentListItem]:
    utcnow = ktp_controller.utils.utcnow()

    raw_abitti2_stats_messages = (
        await ktp_controller.api.client.get_raw_abitti2_stats_messages()
    )
    if len(raw_abitti2_stats_messages) == 0:
        return []

    last_raw_abitti2_stats_message = raw_abitti2_stats_messages[0]

    try:
        raw_abitti2_students = last_raw_abitti2_stats_message["data"]["students"]
    except KeyError:
        return []

    student_list_items = []

    for raw_abitti2_student in raw_abitti2_students:
        # TODO: What if studentBd does not exist or is invalid?
        birthday_ddmmyy: str = raw_abitti2_student["studentBd"]
        birthday: datetime.date = ktp_controller.utils.parse_ddmmyy(birthday_ddmmyy)
        state: str = raw_abitti2_student["studentStatus"]
        update_time: datetime.datetime | None = (
            datetime.datetime.fromisoformat(
                raw_abitti2_student["updateTime"]
            ).astimezone()
            if raw_abitti2_student["updateTime"] is not None
            else None
        )
        exam_finished_at: datetime.datetime | None = (
            datetime.datetime.fromisoformat(
                raw_abitti2_student["examFinishedAt"]
            ).astimezone()
            if raw_abitti2_student["examFinishedAt"] is not None
            else None
        )
        last_changed_at: datetime.datetime | None = None
        if update_time is None and exam_finished_at is None:
            last_changed_at = None
        elif update_time is not None and exam_finished_at is not None:
            last_changed_at = max(update_time, exam_finished_at)
        elif update_time is None:
            last_changed_at = exam_finished_at
        elif exam_finished_at is None:
            last_changed_at = update_time
        else:
            raise RuntimeError("impossible internal logic")

        exam_title: str = raw_abitti2_student["examTitle"]

        state_info = ktp_controller.abitti2.utils.parse_student_state_info(
            raw_abitti2_student,
            utcnow=utcnow,
        )
        if state_info["has_finished"]:
            state = schemas.StudentState.FINISHED
        elif state_info["is_active"]:
            state = schemas.StudentState.ACTIVE
        else:
            state = schemas.StudentState.FLAGGED

        student_list_item = schemas.StudentListItem(
            name=f"{raw_abitti2_student['firstNames']} {raw_abitti2_student['lastName']}",
            birthday=birthday,
            state=state,
            flags=state_info["flags"],
            last_changed_at=last_changed_at,
            exam_title=exam_title,
            student_uuid=raw_abitti2_student["studentUuid"],
            session_uuid=raw_abitti2_student["sessionUuid"],
        )

        student_list_items.append(student_list_item)

    return student_list_items


class _Order(enum.StrEnum):
    ASC = "asc"
    DESC = "desc"


class _StudentListItemSortableField(enum.StrEnum):
    NAME = "name"
    BIRTHDAY = "birthday"
    STATE = "state"
    LAST_CHANGED_AT = "last_changed_at"
    EXAM_TITLE = "exam_title"


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
        await _get_student_list_items(),
        key=lambda x: getattr(x, sort_by),
        reverse=order == "desc",
    )

    if name_birthday_filter:
        query = name_birthday_filter.lower()
        student_list_items = [
            item
            for item in student_list_items
            if query in item.name.lower() or query in item.birthday.isoformat()
        ]

    order_next = "desc" if order == "asc" else "asc"  # Next time the order is reversed

    request.state.locale = session.locale
    _ = ktp_controller.wui.i18n.get_gettext(session.locale)

    column_labels = {
        _StudentListItemSortableField.NAME: _("Name"),
        _StudentListItemSortableField.BIRTHDAY: _("Birthday"),
        _StudentListItemSortableField.STATE: _("State"),
        _StudentListItemSortableField.LAST_CHANGED_AT: _("Last changed at"),
        _StudentListItemSortableField.EXAM_TITLE: _("Exam title"),
    }
    columns = [
        (field.value, column_labels[field], True)
        for field in _StudentListItemSortableField
    ] + [(None, _("Action"), False)]

    state_labels = {
        schemas.StudentState.FINISHED: _("Finished"),
        schemas.StudentState.ACTIVE: _("Active"),
    }
    flag_labels = {
        ktp_controller.schemas.StudentFlag.DISCONNECTED: _("Disconnected"),
        ktp_controller.schemas.StudentFlag.IDLE: _("Idle"),
        ktp_controller.schemas.StudentFlag.WAITING_FOR_AUTH: _("Waiting for auth"),
        ktp_controller.schemas.StudentFlag.UNDEFINED_EXAM: _("Undefined exam"),
        ktp_controller.schemas.StudentFlag.UNKNOWN_ISSUE: _("Unknown issue"),
    }

    context = {
        "student_list_items": student_list_items,
        "columns": columns,
        "state_labels": state_labels,
        "flag_labels": flag_labels,
        "sort_by": sort_by,
        "order_now": order,
        "order_next": order_next,
        "name_birthday_filter": name_birthday_filter,
        "user": session.username,
        "can_end_exam": "wui.invigilator.end-exam" in session.permissions,
    }

    # If the request comes from htmx, return only the table partial
    if request.headers.get("HX-Request"):
        return _templates.TemplateResponse(
            request, name="partials/student_list_table.html.j2", context=context
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
    student_access_code = await ktp_controller.api.client.get_student_access_code()

    request.state.locale = session.locale
    _ = ktp_controller.wui.i18n.get_gettext(session.locale)

    context = {
        "student_access_code": student_access_code,
        "user": session.username,
        "can_change_access_code": (
            "wui.invigilator.change-student-access-code" in session.permissions
        ),
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


async def _end_student_exam(
    *, session_uuid: str, student_uuid: str, username: str
) -> None:
    _LOGGER.info(
        "User %r is ending exam of student %s (session %s)...",
        username,
        student_uuid,
        session_uuid,
    )
    try:
        await ktp_controller.abitti2.client.end_student_exam(
            session_uuid=session_uuid, student_uuid=student_uuid
        )
    except Exception:
        # Runs after the response has been sent, so there is nobody to
        # report the failure to but the log.
        _LOGGER.exception(
            "Failed to end exam of student %s (session %s)",
            student_uuid,
            session_uuid,
        )
        return
    _LOGGER.info("Ended exam of student %s (session %s).", student_uuid, session_uuid)


@router.post(
    "/actions/end-exam",
    status_code=fastapi.status.HTTP_202_ACCEPTED,
    response_class=fastapi.responses.Response,
)
@ktp_controller.wui.auth.require_permission("wui.invigilator.end-exam")
async def _post_end_exam(
    background_tasks: fastapi.BackgroundTasks,
    session_uuid: uuid.UUID = fastapi.Form(...),
    student_uuid: uuid.UUID = fastapi.Form(...),
    session: ktp_controller.wui.auth.Session = fastapi.Depends(
        ktp_controller.wui.auth.get_current_session
    ),
) -> fastapi.responses.Response:
    # Fire-and-forget: the student list refreshes itself via
    # /invigilator/ws once Abitti2 reports the change.
    background_tasks.add_task(
        _end_student_exam,
        session_uuid=str(session_uuid),
        student_uuid=str(student_uuid),
        username=session.username,
    )
    return fastapi.responses.Response(status_code=fastapi.status.HTTP_202_ACCEPTED)


async def _change_student_access_code(*, username: str) -> None:
    _LOGGER.info("User %r is changing the student access code...", username)
    try:
        await ktp_controller.api.client.async_command(
            ktp_controller.messages.Command.CHANGE_STUDENT_ACCESS_CODE
        )
    except Exception:
        # Runs after the response has been sent, so there is nobody to
        # report the failure to but the log.
        _LOGGER.exception("Failed to request a new student access code")
        return
    _LOGGER.info("Requested a new student access code.")


@router.post(
    "/actions/change-student-access-code",
    status_code=fastapi.status.HTTP_202_ACCEPTED,
    response_class=fastapi.responses.Response,
)
@ktp_controller.wui.auth.require_permission(
    "wui.invigilator.change-student-access-code"
)
async def _post_change_student_access_code(
    background_tasks: fastapi.BackgroundTasks,
    session: ktp_controller.wui.auth.Session = fastapi.Depends(
        ktp_controller.wui.auth.get_current_session
    ),
) -> fastapi.responses.Response:
    # Fire-and-forget: the page refreshes itself via /invigilator/ws
    # once the agent reports the new code in a status report.
    background_tasks.add_task(_change_student_access_code, username=session.username)
    return fastapi.responses.Response(status_code=fastapi.status.HTTP_202_ACCEPTED)


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
