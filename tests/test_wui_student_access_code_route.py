import fastapi.testclient
import pytest

import ktp_controller.messages
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


_SAME_ORIGIN_HEADERS = {"origin": "http://testserver"}


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
                    "wui.invigilator.change-student-access-code",
                }
            ),
        )
    )

    response = wui_client.get("/invigilator/student_access_code")

    assert response.status_code == 200
    assert 'class="change-access-code-button"' in response.text
    assert 'id="change-access-code-confirm-overlay"' in response.text
    assert 'hx-post="/invigilator/actions/change-student-access-code"' in response.text


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
    assert "/invigilator/actions/change-student-access-code" not in response.text


def test_change_student_access_code_requires_login(wui_client, mocker):
    async_command_mock = mocker.patch(
        "ktp_controller.api.client.async_command", new=mocker.AsyncMock()
    )

    response = wui_client.post(
        "/invigilator/actions/change-student-access-code",
        headers=_SAME_ORIGIN_HEADERS,
    )

    assert response.status_code == 303
    assert response.headers["location"].startswith("/login")
    async_command_mock.assert_not_called()


def test_change_student_access_code_forbidden_without_permission(
    wui_client, override_session, mocker
):
    async_command_mock = mocker.patch(
        "ktp_controller.api.client.async_command", new=mocker.AsyncMock()
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.invigilator.view"}),
        )
    )

    response = wui_client.post(
        "/invigilator/actions/change-student-access-code",
        headers=_SAME_ORIGIN_HEADERS,
    )

    assert response.status_code == 403
    async_command_mock.assert_not_called()


def test_change_student_access_code_calls_api(wui_client, override_session, mocker):
    async_command_mock = mocker.patch(
        "ktp_controller.api.client.async_command", new=mocker.AsyncMock()
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.invigilator.change-student-access-code"}),
        )
    )

    response = wui_client.post(
        "/invigilator/actions/change-student-access-code",
        headers=_SAME_ORIGIN_HEADERS,
    )

    assert response.status_code == 202
    assert response.content == b""
    async_command_mock.assert_awaited_once_with(
        ktp_controller.messages.Command.CHANGE_STUDENT_ACCESS_CODE
    )


def test_change_student_access_code_logs_api_failure(
    wui_client, override_session, mocker
):
    mocker.patch(
        "ktp_controller.api.client.async_command",
        side_effect=RuntimeError("boom"),
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.invigilator.change-student-access-code"}),
        )
    )

    response = wui_client.post(
        "/invigilator/actions/change-student-access-code",
        headers=_SAME_ORIGIN_HEADERS,
    )

    assert response.status_code == 202
