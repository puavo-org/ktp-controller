# Standard library imports
import collections.abc
import re
import urllib.parse

# Third-party imports
import starlette.datastructures
import starlette.middleware.base
import starlette.requests
import starlette.responses
import starlette.types

# Internal imports
from ktp_controller import SETTINGS

# Relative imports


__all__ = [
    "OriginCheckMiddleware",
    "RootPathFromHeaderMiddleware",
    "SecurityHeadersMiddleware",
]


_CallNext = collections.abc.Callable[
    [starlette.requests.Request],
    collections.abc.Awaitable[starlette.responses.Response],
]

_UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})

_FORWARDED_PREFIX_RE = re.compile(r"\A/remote/[0-9]+\Z")


class RootPathFromHeaderMiddleware:
    """Sets ASGI `root_path` from a nginx-supplied `X-Forwarded-Prefix`.

    WUI may be reached through a reverse proxy that strips a volatile
    `/remote/<id>` prefix before forwarding the request (see
    ktp_controller.nginx.enable_nginx_wui_tls_reverse_proxy). The id isn't
    known at process start, so it can't be a static uvicorn --root-path;
    it must be read per-request instead. This is a plain ASGI middleware
    (not BaseHTTPMiddleware) because BaseHTTPMiddleware passes non-"http"
    scopes through untouched, which would silently skip the "websocket"
    scope used by the live-status socket.
    """

    def __init__(self, app: starlette.types.ASGIApp) -> None:
        self.app = app

    async def __call__(
        self,
        scope: starlette.types.Scope,
        receive: starlette.types.Receive,
        send: starlette.types.Send,
    ) -> None:
        if scope["type"] in ("http", "websocket"):
            headers = starlette.datastructures.Headers(scope=scope)
            prefix = headers.get("x-forwarded-prefix")
            if prefix is not None and _FORWARDED_PREFIX_RE.match(prefix):
                scope = dict(scope)
                scope["root_path"] = prefix

        await self.app(scope, receive, send)


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
            "script-src 'self'; "
            "style-src 'self'; "
            "img-src 'self' data:"
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
