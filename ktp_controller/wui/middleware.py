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
from ktp_controller import SETTINGS, is_prod_mode

# Relative imports


__all__ = [
    "OriginCheckMiddleware",
    "RootPathFromHeaderMiddleware",
    "SecurityHeadersMiddleware",
    "is_origin_accepted",
]


_CallNext = collections.abc.Callable[
    [starlette.requests.Request],
    collections.abc.Awaitable[starlette.responses.Response],
]

_UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})

# A browser-sent Origin header is always http(s), even for a WebSocket
# upgrade request whose own URL scheme is ws(s); normalize the latter
# before comparing the two.
_WEBSOCKET_SCHEME_TO_HTTP_SCHEME = {"ws": "http", "wss": "https"}


def _get_origin_url(
    request: starlette.requests.HTTPConnection,
) -> urllib.parse.SplitResult | None:
    origin_header = request.headers.get("origin")
    if origin_header is not None:
        return urllib.parse.urlsplit(origin_header)

    referer_header = request.headers.get("referer")
    if referer_header is not None:
        return urllib.parse.urlsplit(referer_header)

    return None


def is_origin_accepted(request: starlette.requests.HTTPConnection) -> bool:
    """Checks whether `request`'s Origin/Referer matches its Host.

    Shared by `OriginCheckMiddleware` (HTTP requests) and the live-updates
    WebSocket endpoint (`ktp_controller.wui.live_updates.routes`), since
    Starlette's `BaseHTTPMiddleware` never runs for "websocket" scopes and
    so can't cover the latter itself.
    """
    origin_url = _get_origin_url(request)
    if origin_url is None:
        return False

    if (
        not is_prod_mode()
        and SETTINGS.allow_cross_site_requests_from_localhost_to_wui
        and origin_url.hostname == "localhost"
    ):
        # In development and testing setup, it's possible to allow
        # requests from localhost origin.
        return True

    if origin_url.hostname == SETTINGS.examomatic_host:
        # For requests originating from Exam-O-Matic, port does
        # not matter.
        return origin_url.scheme == "https"

    request_scheme = _WEBSOCKET_SCHEME_TO_HTTP_SCHEME.get(
        request.url.scheme, request.url.scheme
    )
    return (
        origin_url.netloc == request.url.netloc and origin_url.scheme == request_scheme
    )


_FORWARDED_PREFIX_RE = re.compile(r"\A/remote/(?P<id>[0-9]+)\Z")


def _is_valid_forwarded_prefix(prefix: str) -> bool:
    match = _FORWARDED_PREFIX_RE.match(prefix)
    if match is None:
        return False

    # This is /etc/puavo/id in Puavo OS and it must match id of the
    # prefix. Otherwise someone is trying to forward a request which
    # does belong to this KTP Controller.
    return int(match.group("id")) == SETTINGS.id


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
            if prefix is not None:
                if not _is_valid_forwarded_prefix(prefix):
                    # Plain ASGI, not BaseHTTPMiddleware: a Response must be
                    # invoked as an ASGI app to actually send it, returning
                    # it here would silently discard it.
                    response = starlette.responses.PlainTextResponse(
                        "Forbidden: invalid prefix", status_code=403
                    )
                    await response(scope, receive, send)
                    return

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
        if request.method in _UNSAFE_METHODS and not is_origin_accepted(request):
            return starlette.responses.PlainTextResponse(
                "Forbidden: origin check failed", status_code=403
            )

        return await call_next(request)
