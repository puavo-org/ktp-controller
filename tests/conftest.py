# Standard library imports
import dataclasses
import datetime
import difflib
import html.parser
import os.path
import re
import shutil

import fastapi.testclient
import pytest
import selenium.webdriver

# Third-party imports
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Internal imports
import ktp_controller.api.models
import ktp_controller.schemas
import ktp_controller.utils
import ktp_controller.wui.auth
import ktp_controller.wui.main
from ktp_controller import SETTINGS, VERSION
from ktp_controller.api.database import get_db
from ktp_controller.api.main import APP
from ktp_controller.api.models import Base

# Relative imports
from .bot import Abitti2Student


@pytest.fixture
def db_engine():
    # StaticPool keeps the single ":memory:" connection alive across
    # checkouts, for the lifetime of this one test's engine. A fresh
    # engine (and thus a fresh database) per test gives test isolation
    # without wrapping it in one long-lived outer transaction, which
    # would block any code under test (like VACUUM) that needs to run
    # with no transaction open at all.
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    # Mirrors the seed data inserted by
    # alembic/versions/bb0203ef063b_add_users_roles_and_permissions.py,
    # alembic/versions/90f7a03d459e_add_wui_invigilator_end_exam_permission.py,
    # alembic/versions/b84e65b5f7d7_add_wui_invigilator_change_student_.py,
    # alembic/versions/203a49866db9_add_wui_invigilator_set_exam_session_.py
    # and the subsequent wui.actions.* permission-rename migration, which
    # this in-memory schema bypasses.
    with sessionmaker(bind=engine)() as db:
        db.add(
            ktp_controller.api.models.Role(
                dbid=None,
                name="invigilator",
                permissions=[
                    ktp_controller.api.models.Permission(
                        dbid=None, name="wui.invigilator.view"
                    ),
                    ktp_controller.api.models.Permission(
                        dbid=None, name="wui.actions.end-exam"
                    ),
                    ktp_controller.api.models.Permission(
                        dbid=None, name="wui.actions.change-student-access-code"
                    ),
                    ktp_controller.api.models.Permission(
                        dbid=None,
                        name="wui.actions.set-exam-session-permission-to-use-browsers",
                    ),
                ],
            )
        )
        db.commit()
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def testdb(db_engine):
    db = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)()
    yield db
    db.close()


@pytest.fixture
def client(testdb):
    def override_get_db():
        try:
            yield testdb
        finally:
            testdb.close()

    APP.dependency_overrides[get_db] = override_get_db
    yield fastapi.testclient.TestClient(APP)
    APP.dependency_overrides.clear()


@pytest.fixture
def wui_client():
    return fastapi.testclient.TestClient(
        ktp_controller.wui.main.APP, follow_redirects=False
    )


@pytest.fixture
def override_session():
    def _override(session):
        def _get_current_session():
            return session

        ktp_controller.wui.main.APP.dependency_overrides[
            ktp_controller.wui.auth.get_current_session
        ] = _get_current_session

    yield _override
    ktp_controller.wui.main.APP.dependency_overrides.clear()


@pytest.fixture
def anyio_backend():
    # ktp_controller's async code (redis.asyncio, httpx) is asyncio-only;
    # restrict anyio (already pulled in transitively via starlette) to
    # that backend instead of also parametrizing over trio.
    return "asyncio"


@pytest.fixture
def utcnow():
    return datetime.datetime.now(datetime.UTC)


@pytest.fixture
def make_status_report():
    def _make(
        *,
        ktp_controller_version="0.8.0rc10",
        abitti2_version="1.27.0",
        abitti2_domain="what-not.koe.abitti.net",
        abitti2_cert_expires_at="2099-01-01T00:00:00.000+0000",
        puavo_os_image_release="O2611 Broom",
        puavo_os_image_name="opinsys-os-opinsys-bookworm-2026-03-09-100004-amd64.img",
        disk_usage: list[dict] | None = (
            {
                "mountpoint": "/home",
                "total": 100 * 1024**3,
                "used": 80 * 1024**3,
                "free": 20 * 1024**3,
            },
        ),
    ):
        abitti2 = {
            "version": abitti2_version,
            "domain": abitti2_domain,
        }
        if abitti2_cert_expires_at is not None:
            abitti2["cert"] = {
                "domains": [abitti2_domain],
                "expires_at": abitti2_cert_expires_at,
            }
        return {
            "ktp_controller": {
                "version": ktp_controller_version,
                "started_at": "2026-05-03T16:28:51.975+0000",
                "is_auto_control_enabled": True,
            },
            "abitti2": abitti2,
            "os": {
                "puavo_os_image_release": puavo_os_image_release,
                "puavo_os_image_name": puavo_os_image_name,
                "stats": {
                    "disk_usage": (
                        list(disk_usage) if disk_usage is not None else None
                    ),
                },
            },
        }

    return _make


_DEFAULT_V3_STATUS_REPORT_CACHED_FILES = {
    "exams": [
        {
            "path": "/home/puavo-ers/.local/share/ktp-controller/exam-files/c574f93a-ac4d-4441-8679-ca47e565fb7b/exam-file_50d28d5ce4628d9e72c3d42001a49f9fbc146081fbac42610435d6c70d4f6624.mex",
            "size": 25353142,
            "modified_at": "2025-11-05T15:22:26.379+0000",
        }
    ],
    "exam_packages": [
        {
            "path": "/home/puavo-ers/.local/share/ktp-controller/exam-packages/a28618bb-1665-425f-9f35-633a50bbd487/exam-package_a5e52fdc62e2b7b0dd50daabdfd1fbd19de0bea30330de604674aef016da604d.zip",
            "size": 25353354,
            "modified_at": "2026-01-07T17:32:27.423+0000",
        }
    ],
    "answers": [
        {
            "path": "/home/puavo-ers/.local/share/ktp-controller/answer-files/a28618bb-1665-425f-9f35-633a50bbd487/answers-file_2026-01-07T17:34:42.590+0000_final.meb",
            "size": 223604,
            "modified_at": "2026-01-07T17:34:42.968+0000",
        }
    ],
}


@pytest.fixture
def make_v3_status_report(utcnow):
    def _format(value):
        if isinstance(value, datetime.datetime):
            return ktp_controller.utils.strfdt(value)
        return value

    def _make(
        *,
        created_at: datetime.datetime | str | None = None,
        reported_at: datetime.datetime | str | None = None,
        last_message_received_at: datetime.datetime | str | None = None,
        domain: str | None = "funny-server.example.invalid",
        supervisor_passphrase: str = "",
        abitti2_version: str = "",
        exams: list | None = None,
        is_auto_control_enabled: bool = False,
        current_exam_package: dict | None = None,
        next_exam_packages: list | None = (),
        cached_files: dict | None = None,
    ):
        if created_at is None:
            created_at = utcnow
        if reported_at is None:
            reported_at = utcnow
        if last_message_received_at is None:
            last_message_received_at = created_at
        if exams is None:
            exams = []
        if cached_files is None:
            cached_files = _DEFAULT_V3_STATUS_REPORT_CACHED_FILES

        return {
            "v": 3,
            "created_at": _format(created_at),
            "reported_at": _format(reported_at),
            "abitti2": {
                "stats": {"exams": None},
                "answer_count": 0,
                "domain": domain,
                "student_access_code": {
                    "key_code": "1234",
                    "verification_code": "xx",
                },
                "supervisor_username": "valvoja",
                "supervisor_passphrase": supervisor_passphrase,
                "version": abitti2_version,
                "last_message_received_at": _format(last_message_received_at),
                "cert": None,
                "exams": exams,
                "students": [],
            },
            "os": {
                "stats": {
                    "disk_usage": None,
                    "load_average": None,
                    "memory": None,
                    "uptime": None,
                },
                "release": "O2611 Broom (opinsys-os-opinsys-bookworm-2026-03-09-100004-amd64.img)",
                "puavo_os_image_name": "opinsys-os-opinsys-bookworm-2026-03-09-100004-amd64.img",
                "puavo_os_image_release": "O2611 Broom",
            },
            "ktp_controller": {
                "settings": SETTINGS.model_dump(),
                "version": VERSION,
                "started_at": "1970-01-01T01:01:01.010+0000",
                "is_auto_control_enabled": is_auto_control_enabled,
                "current_exam_package": current_exam_package,
                "next_exam_packages": (
                    None if next_exam_packages is None else list(next_exam_packages)
                ),
                "cached_files": cached_files,
                "stats": None,
            },
        }

    return _make


@pytest.fixture(scope="session")
def browser_chrome():
    options = selenium.webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    chrome = selenium.webdriver.Chrome(options=options)
    try:
        yield chrome
    finally:
        chrome.quit()


@pytest.fixture(scope="session")
def browser_firefox():
    options = selenium.webdriver.FirefoxOptions()
    options.add_argument("-headless")
    firefox = selenium.webdriver.Firefox(options=options)
    try:
        yield firefox
    finally:
        firefox.quit()


@pytest.fixture(scope="session")
def student1(browser_firefox):
    return Abitti2Student(browser_firefox)


@pytest.fixture(scope="session")
def student2(browser_chrome):
    return Abitti2Student(browser_chrome)


@dataclasses.dataclass
class _TestRunState:
    scheduled_exam_package1: dict | None = None
    scheduled_exam_package2: dict | None = None
    scheduled_exam_package3: dict | None = None
    student_access_code: ktp_controller.schemas.StudentAccessCode | None = None


@pytest.fixture(scope="session")
def testrunstate():
    return _TestRunState()


@pytest.fixture
def testdir():
    dirpath = os.path.join(os.path.dirname(__file__), "testdir")
    os.makedirs(dirpath)
    yield dirpath
    shutil.rmtree(dirpath)


_VOID_HTML_ELEMENTS = frozenset(
    {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }
)


class _HTMLIndentingPrinter(html.parser.HTMLParser):
    """Re-renders (typically minified) HTML with one tag per line,
    indented by nesting depth, so it reads like a DOM tree instead of a
    single giant line."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._depth = 0
        self.lines: list[str] = []

    def handle_starttag(self, tag, attrs):
        self.lines.append(self._render_tag(tag, attrs))
        if tag not in _VOID_HTML_ELEMENTS:
            self._depth += 1

    def handle_startendtag(self, tag, attrs):
        self.lines.append(self._render_tag(tag, attrs))

    def handle_endtag(self, tag):
        self._depth = max(self._depth - 1, 0)
        self.lines.append(f"{self._indent()}</{tag}>")

    def handle_data(self, data):
        text = data.strip()
        if text:
            self.lines.append(f"{self._indent()}{text}")

    def handle_comment(self, data):
        self.lines.append(f"{self._indent()}<!--{data}-->")

    def handle_decl(self, decl):
        self.lines.append(f"<!{decl}>")

    def _indent(self) -> str:
        return "  " * self._depth

    def _render_tag(self, tag, attrs) -> str:
        attrs_str = "".join(
            f' {name}="{value}"' if value is not None else f" {name}"
            for name, value in attrs
        )
        return f"{self._indent()}<{tag}{attrs_str}>"


def _pretty_print_html(html_text: str) -> list[str]:
    printer = _HTMLIndentingPrinter()
    printer.feed(html_text)
    return printer.lines


def _looks_like_rendered_html(value: object) -> bool:
    # A handful of stray "<"/">" could be anything; a page or an htmx
    # partial has many tags, so this reliably tells apart a rendered
    # response body from a short plain-text comparison value.
    return isinstance(value, str) and value.count("<") > 5


# Matches a single element with no nested tags, e.g.
# '<span class="pill pill-waiting">Waiting</span>' — the same compact,
# single-line shape test snippets are normally written in, so comparing
# against these (rather than the indented pretty-print) is what lets
# difflib actually find the closest rendered match.
_LEAF_ELEMENT_RE = re.compile(r"<([a-zA-Z][\w-]*)\b[^<>]*>[^<>]*</\1>")


def pytest_assertrepr_compare(config, op, left, right):
    """Explain `"..." in response.text`/`"..." not in response.text`
    failures with an indented pretty-print of the HTML and, where
    possible, the closest actually-rendered content, instead of
    pytest's default side-by-side dump of the entire minified page."""
    if op not in ("in", "not in"):
        return None
    if not _looks_like_rendered_html(right) or not isinstance(left, str):
        return None

    pretty_lines = _pretty_print_html(right)
    needle = left.strip()

    if op == "in":
        lines = [f"{left!r} not found in rendered HTML:"]
        leaf_elements = [match.group(0) for match in _LEAF_ELEMENT_RE.finditer(right)]
        matches = difflib.get_close_matches(needle, leaf_elements, n=3, cutoff=0.5)
        if not matches:
            # Not a simple single-element snippet (e.g. it spans
            # several tags); fall back to windows of the pretty-printed
            # lines instead.
            windows = [
                "\n".join(pretty_lines[i : i + 3])
                for i in range(max(len(pretty_lines) - 2, 0))
            ]
            matches = difflib.get_close_matches(needle, windows, n=3, cutoff=0.4)
        if matches:
            lines.append("")
            lines.append("Closest actually-rendered content:")
            for match in matches:
                lines.extend(f"  {match_line}" for match_line in match.splitlines())
                lines.append("  ---")
        else:
            lines.append("")
            lines.append("--- rendered HTML (pretty-printed) ---")
            lines.extend(pretty_lines)
        return lines

    # op == "not in": `left` unexpectedly IS present somewhere in `right`.
    lines = [f"{left!r} unexpectedly found in rendered HTML:", ""]
    found_context = False
    for index, line in enumerate(pretty_lines):
        if needle and needle in line:
            found_context = True
            start = max(index - 2, 0)
            end = min(index + 3, len(pretty_lines))
            lines.extend(f"  {pretty_lines[i]}" for i in range(start, end))
            lines.append("  ---")
    if not found_context:
        lines.append("--- rendered HTML (pretty-printed) ---")
        lines.extend(pretty_lines)
    return lines
