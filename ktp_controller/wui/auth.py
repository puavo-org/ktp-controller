# Standard library imports
import functools
import inspect
import secrets
import typing

# Third-party imports
import fastapi

# Internal imports
import ktp_controller.api.client
import ktp_controller.redis
from ktp_controller import SETTINGS

# Relative imports


__all__ = [
    # Constants:
    "SESSION_COOKIE_NAME",
    # Types:
    "NotAuthenticatedError",
    "Session",
    # Utils:
    "authenticate",
    "create_session",
    "destroy_session",
    "get_current_session",
    "require_permission",
]


# Constants:


SESSION_COOKIE_NAME = "ktp_controller_session"

_SESSION_STORE = ktp_controller.redis.SessionStore("wui", SETTINGS.session_ttl_sec)


# Types:


class NotAuthenticatedError(Exception):
    """Raised by get_current_session() when no valid session cookie is present."""


class Session(typing.NamedTuple):
    session_id: str
    username: str
    permissions: frozenset[str]


# Utils:


async def authenticate(username: str, password: str) -> bool:
    """Validates credentials the same way the former HTTP Basic Auth did:
    against Abitti2's own live, rotating invigilator passphrase."""
    last_status_report = await ktp_controller.api.client.get_last_status_report()
    if (
        last_status_report is None
        or last_status_report["abitti2"]["supervisor_passphrase"] is None
    ):
        raise RuntimeError("invigilator's passphrase is unavailable")

    # Use secrets.compare_digest to protect against timing attacks
    is_correct_username = secrets.compare_digest(
        username, last_status_report["abitti2"]["supervisor_username"]
    )
    is_correct_password = secrets.compare_digest(
        password, last_status_report["abitti2"]["supervisor_passphrase"]
    )

    return is_correct_username and is_correct_password


async def create_session(username: str) -> str:
    permissions = await ktp_controller.api.client.get_or_create_user_permissions(
        username
    )
    return await _SESSION_STORE.create(
        {"username": username, "permissions": permissions}
    )


async def destroy_session(session_id: str) -> None:
    await _SESSION_STORE.delete(session_id)


async def get_current_session(request: fastapi.Request) -> Session:
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if session_id is None:
        raise NotAuthenticatedError

    data = await _SESSION_STORE.get(session_id)
    if data is None:
        raise NotAuthenticatedError

    await _SESSION_STORE.touch(session_id)

    return Session(
        session_id=session_id,
        username=data["username"],
        permissions=frozenset(data["permissions"]),
    )


def require_permission(
    permission: str, /
) -> typing.Callable[
    [typing.Callable[..., typing.Any]], typing.Callable[..., typing.Any]
]:
    """Endpoint decorator enforcing that the current session has `permission`.

    The decorated endpoint must declare a
    `session: Session = fastapi.Depends(get_current_session)` parameter;
    the wrapper preserves the original signature (via __signature__) so
    FastAPI's dependency injection still resolves every parameter,
    including that one.
    """

    def decorator(
        func: typing.Callable[..., typing.Any],
    ) -> typing.Callable[..., typing.Any]:
        @functools.wraps(func)
        async def wrapper(*args: typing.Any, **kwargs: typing.Any) -> typing.Any:
            session = kwargs.get("session")
            if not isinstance(session, Session):
                raise RuntimeError(
                    "@require_permission requires the endpoint to declare a "
                    "'session: Session = fastapi.Depends(get_current_session)' "
                    "parameter"
                )
            if permission not in session.permissions:
                raise fastapi.HTTPException(
                    status_code=fastapi.status.HTTP_403_FORBIDDEN,
                    detail="Forbidden",
                )
            return await func(*args, **kwargs)

        wrapper.__signature__ = inspect.signature(func)  # type: ignore[attr-defined]
        return wrapper

    return decorator
