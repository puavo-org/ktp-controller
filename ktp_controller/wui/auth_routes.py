# Standard library imports
import logging
import os.path

# Third-party imports
import fastapi
import fastapi.responses
import fastapi.templating

# Internal imports
import ktp_controller.redis
from ktp_controller import SETTINGS

# Relative imports
from . import auth

_LOGGER = logging.getLogger(__name__)


__all__ = [
    "router",
]

router = fastapi.APIRouter(tags=["auth"])

_thisdir = os.path.dirname(__file__)
_templates = fastapi.templating.Jinja2Templates(
    directory=os.path.join(_thisdir, "templates")
)

_DEFAULT_NEXT_PATH = "/invigilator/"

# Slows down brute-forcing of the login form. Keyed by the immediate
# peer address; this app isn't behind nginx yet (see architecture
# notes), so there's no forwarded-for header to trust instead.
_LOGIN_RATE_LIMITER = ktp_controller.redis.RateLimiter("login", 10, 300)


@router.get("/login", response_class=fastapi.responses.HTMLResponse)
async def _get_login(
    request: fastapi.Request,
    next: str = _DEFAULT_NEXT_PATH,
    session: auth.Session | None = fastapi.Depends(auth.get_optional_session),
) -> fastapi.responses.HTMLResponse:
    return _templates.TemplateResponse(
        request,
        name="login.html.j2",
        context={"next": next, "error": None, "session": session},
    )


@router.post("/login")
async def _post_login(
    request: fastapi.Request,
    username: str = fastapi.Form(...),
    password: str = fastapi.Form(...),
    next: str = fastapi.Form(_DEFAULT_NEXT_PATH),
) -> fastapi.responses.Response:
    client_ip = request.client.host if request.client is not None else "unknown"
    if not await _LOGIN_RATE_LIMITER.hit(client_ip):
        _LOGGER.warning("login rate limit exceeded for %r", client_ip)
        return fastapi.responses.PlainTextResponse(
            "Too many login attempts, please try again later.",
            status_code=fastapi.status.HTTP_429_TOO_MANY_REQUESTS,
        )

    if not await auth.authenticate(username, password):
        return _templates.TemplateResponse(
            request,
            name="login.html.j2",
            context={
                "next": next,
                "error": "Incorrect username or password",
                "session": None,
            },
            status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
        )

    session_id = await auth.create_session(username)

    response: fastapi.responses.Response = fastapi.responses.RedirectResponse(
        url=next, status_code=fastapi.status.HTTP_303_SEE_OTHER
    )
    response.set_cookie(
        auth.SESSION_COOKIE_NAME,
        session_id,
        max_age=SETTINGS.session_ttl_sec,
        httponly=True,
        secure=SETTINGS.session_cookie_secure,
        samesite="lax",
    )
    return response


@router.post("/logout")
async def _post_logout(request: fastapi.Request) -> fastapi.responses.Response:
    session_id = request.cookies.get(auth.SESSION_COOKIE_NAME)
    if session_id is not None:
        await auth.destroy_session(session_id)

    response: fastapi.responses.Response = fastapi.responses.RedirectResponse(
        url="/login", status_code=fastapi.status.HTTP_303_SEE_OTHER
    )
    response.delete_cookie(auth.SESSION_COOKIE_NAME)
    return response
