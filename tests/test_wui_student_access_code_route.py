import fastapi.testclient
import pytest

import ktp_controller.schemas
import ktp_controller.wui.auth
import ktp_controller.wui.main
from tests.test_wui_invigilator_route import _mock_abitti2_state


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
    assert 'id="student-state-counts" hx-swap-oob="true"' in response.text
    assert '<span class="pill pill-has_problems">Has problems 1</span>' in (
        response.text
    )
    assert '<span class="pill pill-in_exam">In exam 1</span>' in response.text
    assert '<span class="pill pill-finished">Finished 1</span>' in response.text
    assert '<span class="pill pill-waiting">Waiting 1</span>' in response.text
