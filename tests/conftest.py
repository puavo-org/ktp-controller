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

# Internal imports
import ktp_controller.api.models
import ktp_controller.schemas
from ktp_controller.api.database import get_db
from ktp_controller.api.main import APP
from ktp_controller.api.models import Base

# Relative imports
from .bot import Abitti2Student


@pytest.fixture(scope="session")
def db_engine():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
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


@pytest.fixture
def testdb(db_engine):
    connection = db_engine.connect()
    transaction = connection.begin()
    db = sessionmaker(autocommit=False, autoflush=False, bind=connection)()
    yield db
    db.close()
    transaction.rollback()
    connection.close()


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
def anyio_backend():
    # ktp_controller's async code (redis.asyncio, httpx) is asyncio-only;
    # restrict anyio (already pulled in transitively via starlette) to
    # that backend instead of also parametrizing over trio.
    return "asyncio"


@pytest.fixture
def utcnow():
    return datetime.datetime.utcnow().replace(tzinfo=datetime.UTC)


@pytest.fixture(scope="session")
def browser_chrome():
    chrome = selenium.webdriver.Chrome()
    try:
        yield chrome
    finally:
        chrome.quit()


@pytest.fixture(scope="session")
def browser_firefox():
    firefox = selenium.webdriver.Firefox()
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
