# Standard library imports
import collections.abc
import urllib.parse

# Third-party imports
import starlette.middleware.base
import starlette.requests
import starlette.responses

# Internal imports
from ktp_controller import SETTINGS

# Relative imports


__all__ = [
    "OriginCheckMiddleware",
    "SecurityHeadersMiddleware",
]


_CallNext = collections.abc.Callable[
    [starlette.requests.Request],
    collections.abc.Awaitable[starlette.responses.Response],
]

_UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


class SecurityHeadersMiddleware(starlette.middleware.base.BaseHTTPMiddleware):
    async def dispatch(
        self, request: starlette.requests.Request, call_next: _CallNext
    ) -> starlette.responses.Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' https://unpkg.com; "
            "style-src 'self' 'unsafe-inline'"
        )
        if SETTINGS.session_cookie_secure:
            # A no-op until nginx terminates TLS in front of this app, but
            # ready for it; nginx may additionally set this itself.
            response.headers["Strict-Transport-Security"] = (
                "max-age=63072000; includeSubDomains"
            )
        return response


class OriginCheckMiddleware(starlette.middleware.base.BaseHTTPMiddleware):
    """Rejects state-changing requests whose Origin/Referer doesn't match Host.

    This is a defense-in-depth CSRF mitigation layered on top of the
    session cookie's SameSite=Lax attribute (which already keeps
    browsers from attaching it to cross-site POSTs). It never reads the
    request body, so it can't interfere with a downstream endpoint's
    own form/JSON parsing.
    """

    async def dispatch(
        self, request: starlette.requests.Request, call_next: _CallNext
    ) -> starlette.responses.Response:
        if request.method in _UNSAFE_METHODS:
            origin = self.__request_origin(request)
            if origin is None or origin != request.url.netloc:
                return starlette.responses.PlainTextResponse(
                    "Forbidden: origin check failed", status_code=403
                )

        return await call_next(request)

    @staticmethod
    def __request_origin(request: starlette.requests.Request) -> str | None:
        origin_header = request.headers.get("origin")
        if origin_header is not None:
            return urllib.parse.urlsplit(origin_header).netloc

        referer_header = request.headers.get("referer")
        if referer_header is not None:
            return urllib.parse.urlsplit(referer_header).netloc

        return None
