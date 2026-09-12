# Standard library imports
import datetime
import enum
import os.path
import secrets

# Third-party imports
import fastapi
import fastapi.responses
import fastapi.security
import fastapi.templating

# Internal imports
import ktp_controller.api.client

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
_security = fastapi.security.HTTPBasic()

_SAMPLE_DATA: list[schemas.StudentListItem] = [
    schemas.StudentListItem(
        name="Alice Smith",
        birthday=datetime.date(1982, 2, 1),
        state="Passed",
        last_changed_at=datetime.datetime(2026, 3, 10, 14, 30, tzinfo=datetime.UTC),
        exam_title="Python Professional",
    ),
    schemas.StudentListItem(
        name="Bob Jones",
        birthday=datetime.date(1956, 2, 1),
        state="Pending",
        last_changed_at=datetime.datetime(2026, 3, 12, 9, 15, tzinfo=datetime.UTC),
        exam_title="AWS Cloud Practitioner",
    ),
    schemas.StudentListItem(
        name="Charlie Brown",
        birthday=datetime.date(1966, 12, 7),
        state="Failed",
        last_changed_at=datetime.datetime(2026, 3, 1, 11, 45, tzinfo=datetime.UTC),
        exam_title="Data Science Fundamentals",
    ),
    schemas.StudentListItem(
        name="Diana Prince",
        birthday=datetime.date(2009, 9, 9),
        state="Passed",
        last_changed_at=datetime.datetime(2026, 3, 11, 16, 0, tzinfo=datetime.UTC),
        exam_title="Cybersecurity Basics",
    ),
    schemas.StudentListItem(
        name="Ethan Hunt",
        birthday=datetime.date(1977, 11, 11),
        state="In Review",
        last_changed_at=datetime.datetime(2026, 3, 8, 8, 20, tzinfo=datetime.UTC),
        exam_title="DevOps Fundamentals",
    ),
]


async def _authenticate_invigilator(
    credentials: fastapi.security.HTTPBasicCredentials = fastapi.Depends(_security),
) -> str:
    """Validates HTTP Basic Auth credentials."""
    last_status_report = await ktp_controller.api.client.get_last_status_report()
    if (
        last_status_report is None
        or last_status_report["abitti2"]["supervisor_passphrase"] is None
    ):
        raise RuntimeError("invigilator's passphrase is unavailable")

    # Use secrets.compare_digest to protect against timing attacks
    is_correct_username = secrets.compare_digest(
        credentials.username, last_status_report["abitti2"]["supervisor_username"]
    )
    is_correct_password = secrets.compare_digest(
        credentials.password, last_status_report["abitti2"]["supervisor_passphrase"]
    )

    if not (is_correct_username and is_correct_password):
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )

    return credentials.username


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
def _get_invigilator(
    request: fastapi.Request,
    sort_by: _StudentListItemSortableField = _StudentListItemSortableField.NAME,
    order: _Order = _Order.ASC,
    name_birthday_filter: str = "",
    user: str = fastapi.Depends(
        _authenticate_invigilator
    ),  # Enforces Basic Auth with invigilator's credentials
) -> fastapi.responses.HTMLResponse:
    sortable_keys = list(schemas.StudentListItem.schema()["properties"])

    student_list_items = sorted(
        _SAMPLE_DATA,
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
        "user": user,
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
