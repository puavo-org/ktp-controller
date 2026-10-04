import fastapi.testclient
import pytest

import ktp_controller.schemas
import ktp_controller.wui.auth
import ktp_controller.wui.main


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
        "ktp_controller.api.client.get_student_access_code",
        return_value=ktp_controller.schemas.StudentAccessCode(
            key_code="1234", verification_code="xx"
        ),
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
    assert "1234 xx" in response.text
    assert b"alice" in response.content


def test_student_access_code_view_shows_students_nav_link(
    wui_client, override_session, mocker
):
    mocker.patch("ktp_controller.api.client.get_student_access_code", return_value=None)
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
    mocker.patch("ktp_controller.api.client.get_student_access_code", return_value=None)
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
    assert "No access code available" in response.text


def test_student_access_code_view_forbidden_without_permission(
    wui_client, override_session, mocker
):
    mocker.patch("ktp_controller.api.client.get_student_access_code", return_value=None)
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
    mocker.patch("ktp_controller.api.client.get_student_access_code", return_value=None)
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
    mocker.patch("ktp_controller.api.client.get_student_access_code", return_value=None)
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
