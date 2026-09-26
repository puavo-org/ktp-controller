# Standard library imports
import datetime
import functools
import gettext
import os.path
import typing

# Third-party imports
import babel
import babel.dates
import fastapi
import jinja2
import jinja2.runtime
import markupsafe

# Internal imports
from ktp_controller import SETTINGS

# Relative imports
from . import auth

__all__ = [
    "get_gettext",
    "get_locale",
    "localize_date",
    "localize_datetime",
    "negotiate_locale",
    "template_context_processor",
    "translate_labels",
]

_LOCALE_DIR = os.path.join(os.path.dirname(__file__), "locale")
_DOMAIN = "messages"


def _parse_accept_language(header_value: str) -> list[str]:
    """Returns primary language subtags from an Accept-Language header,
    ordered by descending q-value."""
    entries: list[tuple[str, float]] = []
    for part in header_value.split(","):
        part = part.strip()
        if not part:
            continue
        tag, _sep, qstr = part.partition(";q=")
        try:
            q = float(qstr.strip()) if qstr else 1.0
        except ValueError:
            q = 1.0
        entries.append((tag.strip().split("-")[0].lower(), q))
    entries.sort(key=lambda entry: entry[1], reverse=True)
    return [tag for tag, _q in entries]


def negotiate_locale(accept_language_header: str | None) -> str:
    if not accept_language_header:
        return SETTINGS.default_locale

    preferred = _parse_accept_language(accept_language_header)
    negotiated = babel.Locale.negotiate(preferred, SETTINGS.supported_locales)
    return str(negotiated) if negotiated is not None else SETTINGS.default_locale


async def get_locale(
    request: fastapi.Request,
    session: auth.Session | None = fastapi.Depends(auth.get_optional_session),
) -> str:
    """Resolves the effective locale for the current request.

    Precedence: an explicit `lang` query param or form field (used by the
    pre-login language switcher), then the session's stored choice, then
    Accept-Language negotiation. Also stashes the result on
    `request.state.locale`, since the (synchronous) Jinja2 context
    processor cannot itself run this async dependency.
    """
    lang = request.query_params.get("lang")
    if lang is None and request.method == "POST":
        form = await request.form()
        lang_value = form.get("lang")
        lang = lang_value if isinstance(lang_value, str) else None

    if lang is not None and lang in SETTINGS.supported_locales:
        locale = lang
    elif session is not None:
        locale = session.locale
    else:
        locale = negotiate_locale(request.headers.get("accept-language"))

    request.state.locale = locale
    return locale


@functools.cache
def _get_translations(locale: str) -> gettext.NullTranslations:
    return gettext.translation(_DOMAIN, _LOCALE_DIR, languages=[locale], fallback=True)


def get_gettext(locale: str) -> typing.Callable[[str], str]:
    return _get_translations(locale).gettext


def _newstyle_gettext(
    gettext_func: typing.Callable[[str], str],
) -> typing.Callable[..., str]:
    """Wraps a plain gettext() as Jinja2's i18n extension expects: taking
    keyword variables and %-formatting the translated string with them,
    matching the "newstyle" gettext behavior used by `{% trans %}`/`_()`."""

    @jinja2.pass_context
    def gettext(
        context: jinja2.runtime.Context, string: str, **variables: typing.Any
    ) -> str:
        rv = gettext_func(string)
        if context.eval_ctx.autoescape:
            rv = markupsafe.Markup(rv)
        return rv % variables

    return gettext


def _newstyle_ngettext(
    ngettext_func: typing.Callable[[str, str, int], str],
) -> typing.Callable[..., str]:
    @jinja2.pass_context
    def ngettext(
        context: jinja2.runtime.Context,
        singular: str,
        plural: str,
        num: int,
        **variables: typing.Any,
    ) -> str:
        variables.setdefault("num", num)
        rv = ngettext_func(singular, plural, num)
        if context.eval_ctx.autoescape:
            rv = markupsafe.Markup(rv)
        return rv % variables

    return ngettext


def template_context_processor(request: fastapi.Request) -> dict[str, typing.Any]:
    locale = getattr(request.state, "locale", SETTINGS.default_locale)
    translations = _get_translations(locale)
    return {
        "locale": locale,
        "gettext": _newstyle_gettext(translations.gettext),
        "ngettext": _newstyle_ngettext(translations.ngettext),
    }


def localize_date(d: datetime.date, locale: str) -> str:
    # Babel's "short" format truncates the year to two digits in some
    # locales (e.g. en: "1/1/05"), which is ambiguous for a birthday. The
    # "yMd" skeleton keeps a full four-digit year while still following
    # each locale's usual field order.
    return babel.dates.format_skeleton("yMd", d, locale=locale)


def localize_datetime(dt: datetime.datetime, locale: str) -> str:
    return babel.dates.format_datetime(dt, format="short", locale=locale)


def translate_labels(
    values: typing.Iterable[typing.Any], labels: dict[typing.Any, str]
) -> str:
    return ", ".join(labels.get(v, v) for v in sorted(values)) or "-"
