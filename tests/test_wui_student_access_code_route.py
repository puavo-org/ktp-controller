import datetime

import pytest

import ktp_controller.schemas
import ktp_controller.wui.auth
import ktp_controller.wui.main
from tests.html_helpers import _nav_item_tag
from tests.test_wui_invigilator_route import _mock_abitti2_state


@pytest.fixture(autouse=True)
def _mock_last_status_report(mocker):
    # This page doesn't otherwise care about the status report; it only
    # needs nav_severity's get_last_status_report() call to not hit the
    # network. Tests exercising nav_severity itself override this with
    # their own mocker.patch(...).
    mocker.patch("ktp_controller.api.client.get_last_status_report", return_value=None)


def test_student_access_code_view_requires_login(wui_client):
    response = wui_client.get("/invigilator/student_access_code")

    assert response.status_code == 303
    assert response.headers["location"].startswith("/login")


def test_student_access_code_view_allowed_with_permission(
    wui_client, override_session, mocker
):
    mocker.patch(
        "ktp_controller.api.client.get_student_access_code_and_server_name",
        return_value=ktp_controller.schemas.StudentAccessCodeAndServerName(
            student_access_code=ktp_controller.schemas.StudentAccessCode(
                key_code="1234", verification_code="xx"
            ),
            server_name="top-men",
        ),
    )
    mocker.patch(
        "ktp_controller.api.client.get_raw_abitti2_stats_messages", return_value=[]
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.invigilator.view"}),
        )
    )

    response = wui_client.get("/invigilator/student_access_code")

    assert response.status_code == 200
    assert "top-men" in response.text
    assert "1234 xx" in response.text
    assert b"alice" in response.content


def test_student_access_code_view_hides_nav_warning_by_default(
    wui_client, override_session, mocker
):
    mocker.patch(
        "ktp_controller.api.client.get_student_access_code_and_server_name",
        return_value=None,
    )
    mocker.patch(
        "ktp_controller.api.client.get_raw_abitti2_stats_messages", return_value=[]
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.invigilator.view"}),
            locale="en",
        )
    )

    response = wui_client.get("/invigilator/student_access_code")

    assert response.status_code == 200
    nav_item = _nav_item_tag(response.text, "Exam server")
    assert "value-warning" not in nav_item
    assert "severity-icon" not in nav_item
    assert 'hx-get="/nav_status"' in nav_item
    assert 'hx-trigger="live-update from:body throttle:2s"' in nav_item
    assert "static/page_refreshed_status.js" in response.text
    assert 'id="page-refreshed-status"' in response.text
    assert 'data-template-one="Page refreshed {n} second ago"' in response.text
    assert 'data-template-other="Page refreshed {n} seconds ago"' in response.text


def test_student_access_code_view_shows_nav_warning_for_soon_expiring_cert(
    wui_client, override_session, mocker, make_status_report
):
    mocker.patch(
        "ktp_controller.api.client.get_student_access_code_and_server_name",
        return_value=None,
    )
    mocker.patch(
        "ktp_controller.api.client.get_raw_abitti2_stats_messages", return_value=[]
    )
    mocker.patch(
        "ktp_controller.api.client.get_last_status_report",
        return_value=make_status_report(
            abitti2_cert_expires_at=(
                datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=1)
            ).isoformat()
        ),
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.invigilator.view"}),
            locale="en",
        )
    )

    response = wui_client.get("/invigilator/student_access_code")

    assert response.status_code == 200
    nav_item = _nav_item_tag(response.text, "Exam server")
    assert "value-warning" in nav_item
    assert "severity-icon" in nav_item


def test_student_access_code_view_shows_students_nav_link(
    wui_client, override_session, mocker
):
    mocker.patch(
        "ktp_controller.api.client.get_student_access_code_and_server_name",
        return_value=None,
    )
    mocker.patch(
        "ktp_controller.api.client.get_raw_abitti2_stats_messages", return_value=[]
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.invigilator.view"}),
        )
    )

    response = wui_client.get("/invigilator/student_access_code")

    assert response.status_code == 200
    assert 'href="/invigilator/"' in response.text


def test_student_access_code_view_shows_placeholder_without_code(
    wui_client, override_session, mocker
):
    mocker.patch(
        "ktp_controller.api.client.get_student_access_code_and_server_name",
        return_value=None,
    )
    mocker.patch(
        "ktp_controller.api.client.get_raw_abitti2_stats_messages", return_value=[]
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.invigilator.view"}),
            locale="en",
        )
    )

    response = wui_client.get("/invigilator/student_access_code")

    assert response.status_code == 200
    assert "No server name available" in response.text
    assert "No access code available" in response.text


def test_student_access_code_view_forbidden_without_permission(
    wui_client, override_session, mocker
):
    mocker.patch(
        "ktp_controller.api.client.get_student_access_code_and_server_name",
        return_value=None,
    )
    mocker.patch(
        "ktp_controller.api.client.get_raw_abitti2_stats_messages", return_value=[]
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset(),
        )
    )

    response = wui_client.get("/invigilator/student_access_code")

    assert response.status_code == 403


def test_student_access_code_view_shows_change_button_with_permission(
    wui_client, override_session, mocker
):
    mocker.patch(
        "ktp_controller.api.client.get_student_access_code_and_server_name",
        return_value=None,
    )
    mocker.patch(
        "ktp_controller.api.client.get_raw_abitti2_stats_messages", return_value=[]
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset(
                {
                    "wui.invigilator.view",
                    "wui.actions.change-student-access-code",
                }
            ),
        )
    )

    response = wui_client.get("/invigilator/student_access_code")

    assert response.status_code == 200
    assert 'class="change-access-code-button"' in response.text
    assert 'id="change-access-code-confirm-overlay"' in response.text
    assert 'hx-post="/actions/change-student-access-code"' in response.text


def test_student_access_code_view_hides_change_button_without_permission(
    wui_client, override_session, mocker
):
    mocker.patch(
        "ktp_controller.api.client.get_student_access_code_and_server_name",
        return_value=None,
    )
    mocker.patch(
        "ktp_controller.api.client.get_raw_abitti2_stats_messages", return_value=[]
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.invigilator.view"}),
        )
    )

    response = wui_client.get("/invigilator/student_access_code")

    assert response.status_code == 200
    assert "change-access-code-button" not in response.text
    assert "/actions/change-student-access-code" not in response.text


def test_student_access_code_view_renders_student_state_counts(
    wui_client, override_session, mocker
):
    mocker.patch(
        "ktp_controller.api.client.get_student_access_code_and_server_name",
        return_value=None,
    )
    _mock_abitti2_state(
        mocker,
        student_count=4,
        student_statuses=[
            "in-exam-browser",
            "waiting-for-auth-browser",
            "exam-finished-by-supo",
            "in-exam-browser",
        ],
        is_connecteds=[True, True, True, False],
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.invigilator.view"}),
            locale="en",
        )
    )

    response = wui_client.get("/invigilator/student_access_code")

    assert response.status_code == 200
    # Exactly once: rendered via the common header only.
    assert response.text.count('id="student-state-counts"') == 1
    assert '<span class="pill pill-has_problems">Has problems 1</span>' in (
        response.text
    )
    assert '<span class="pill pill-in_exam">In exam 1</span>' in response.text
    assert '<span class="pill pill-finished">Finished 1</span>' in response.text
    assert '<span class="pill pill-waiting">Waiting 1</span>' in response.text


def test_student_access_code_view_student_state_counts_present_in_htmx_partial(
    wui_client, override_session, mocker
):
    mocker.patch(
        "ktp_controller.api.client.get_student_access_code_and_server_name",
        return_value=None,
    )
    _mock_abitti2_state(
        mocker,
        student_count=4,
        student_statuses=[
            "in-exam-browser",
            "waiting-for-auth-browser",
            "exam-finished-by-supo",
            "in-exam-browser",
        ],
        is_connecteds=[True, True, True, False],
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.invigilator.view"}),
            locale="en",
        )
    )

    response = wui_client.get(
        "/invigilator/student_access_code", headers={"HX-Request": "true"}
    )

    assert response.status_code == 200
    assert (
        'id="student-state-counts" class="state-counts" hx-swap-oob="true"'
        in response.text
    )
    assert '<span class="pill pill-has_problems">Has problems 1</span>' in (
        response.text
    )
    assert '<span class="pill pill-in_exam">In exam 1</span>' in response.text
    assert '<span class="pill pill-finished">Finished 1</span>' in response.text
    assert '<span class="pill pill-waiting">Waiting 1</span>' in response.text
