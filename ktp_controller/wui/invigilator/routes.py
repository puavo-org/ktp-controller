# Standard library imports
import datetime
import enum
import os.path

# Third-party imports
import fastapi
import fastapi.responses
import fastapi.templating

# Internal imports
import ktp_controller.api.client
import ktp_controller.wui.auth

# Relative imports
from . import schemas

__all__ = [
    "router",
]

router = fastapi.APIRouter(tags=["htmx"])
_thisdir = os.path.dirname(__file__)
_templates = fastapi.templating.Jinja2Templates(
    directory=os.path.join(_thisdir, "templates")
)


async def _get_student_list_items() -> list[schemas.StudentListItem]:
    raw_abitti2_stats_messages = (
        await ktp_controller.api.client.get_raw_abitti2_stats_messages()
    )
    if len(raw_abitti2_stats_messages) == 0:
        return []

    last_raw_abitti2_stats_message = raw_abitti2_stats_messages[-1]

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

        student_list_item = schemas.StudentListItem(
            name=f"{raw_abitti2_student['firstNames']} {raw_abitti2_student['lastName']}",
            birthday=birthday,
            state=state,
            last_changed_at=last_changed_at,
            exam_title=exam_title,
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
    sortable_keys = list(schemas.StudentListItem.schema()["properties"])

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

    columns = [(k, k.replace("_", " ").capitalize()) for k in sortable_keys]

    context = {
        "student_list_items": student_list_items,
        "columns": columns,
        "sort_by": sort_by,
        "order_now": order,
        "order_next": order_next,
        "name_birthday_filter": name_birthday_filter,
        "user": session.username,
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
