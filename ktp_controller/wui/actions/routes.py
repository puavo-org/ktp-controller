# Standard library imports
import logging
import uuid

# Third-party imports
import fastapi
import fastapi.responses

# Internal imports
import ktp_controller.abitti2.client
import ktp_controller.api.client
import ktp_controller.messages
import ktp_controller.wui.auth

__all__ = [
    "router",
]

_LOGGER = logging.getLogger(__name__)

router = fastapi.APIRouter(tags=["htmx"])


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
    "/end-exam",
    status_code=fastapi.status.HTTP_202_ACCEPTED,
    response_class=fastapi.responses.Response,
)
@ktp_controller.wui.auth.require_permission("wui.actions.end-exam")
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
    "/change-student-access-code",
    status_code=fastapi.status.HTTP_202_ACCEPTED,
    response_class=fastapi.responses.Response,
)
@ktp_controller.wui.auth.require_permission("wui.actions.change-student-access-code")
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


async def _set_exam_session_permission_to_use_browsers(
    *, session_uuid: str, student_uuid: str, allow: bool, username: str
) -> None:
    _LOGGER.info(
        "User %r is setting browser-use permission for session %s to %s...",
        username,
        session_uuid,
        allow,
    )
    try:
        await ktp_controller.api.client.async_command(
            ktp_controller.messages.Command.SET_EXAM_SESSION_PERMISSION_TO_USE_BROWSERS,
            session_uuid=session_uuid,
            student_uuid=student_uuid,
            allow=allow,
        )
    except Exception:
        # Runs after the response has been sent, so there is nobody to
        # report the failure to but the log.
        _LOGGER.exception(
            "Failed to set browser-use permission for session %s", session_uuid
        )
        return
    _LOGGER.info(
        "Requested browser-use permission change for session %s.", session_uuid
    )


@router.post(
    "/set-exam-session-permission-to-use-browsers",
    status_code=fastapi.status.HTTP_202_ACCEPTED,
    response_class=fastapi.responses.Response,
)
@ktp_controller.wui.auth.require_permission(
    "wui.actions.set-exam-session-permission-to-use-browsers"
)
async def _post_set_exam_session_permission_to_use_browsers(
    background_tasks: fastapi.BackgroundTasks,
    session_uuid: uuid.UUID = fastapi.Form(...),
    student_uuid: uuid.UUID = fastapi.Form(...),
    # A checkbox is only submitted when checked, per standard HTML form
    # semantics (which htmx follows for its own triggering element), so a
    # missing "allow" field means the checkbox was unchecked.
    allow: bool = fastapi.Form(False),
    session: ktp_controller.wui.auth.Session = fastapi.Depends(
        ktp_controller.wui.auth.get_current_session
    ),
) -> fastapi.responses.Response:
    # Fire-and-forget: the student list refreshes itself via
    # /invigilator/ws once Abitti2 reports the change.
    background_tasks.add_task(
        _set_exam_session_permission_to_use_browsers,
        session_uuid=str(session_uuid),
        student_uuid=str(student_uuid),
        allow=allow,
        username=session.username,
    )
    return fastapi.responses.Response(status_code=fastapi.status.HTTP_202_ACCEPTED)
