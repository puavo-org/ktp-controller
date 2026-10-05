import fastapi.testclient
import pytest
import starlette.testclient

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


def test_invigilator_view_requires_login(wui_client):
    response = wui_client.get("/invigilator/")

    assert response.status_code == 303
    assert response.headers["location"].startswith("/login")


def test_invigilator_view_allowed_with_permission(wui_client, override_session, mocker):
    mocker.patch(
        "ktp_controller.api.client.get_raw_abitti2_stats_messages",
        return_value=[],
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.invigilator.view"}),
        )
    )

    response = wui_client.get("/invigilator/")

    assert response.status_code == 200
    assert b"alice" in response.content
    assert b'action="/logout"' in response.content


def test_invigilator_view_shows_student_access_code_nav_link(
    wui_client, override_session, mocker
):
    mocker.patch(
        "ktp_controller.api.client.get_raw_abitti2_stats_messages",
        return_value=[],
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.invigilator.view"}),
        )
    )

    response = wui_client.get("/invigilator/")

    assert response.status_code == 200
    assert 'href="/invigilator/student_access_code"' in response.text


def test_invigilator_view_renders_connection_lost_overlay(
    wui_client, override_session, mocker
):
    mocker.patch(
        "ktp_controller.api.client.get_raw_abitti2_stats_messages",
        return_value=[],
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.invigilator.view"}),
        )
    )

    response = wui_client.get("/invigilator/")

    assert response.status_code == 200
    assert 'id="connection-lost-overlay"' in response.text


_STUDENT_UUID = "0b7f4c5e-2a55-4c34-9a8c-7e4f0d3a1b21"
_SESSION_UUID = "5d2e8f1a-6b3c-4d9e-8f7a-1c2b3d4e5f60"


def _raw_abitti2_stats_messages(
    *,
    is_allowed_to_use_browser=None,
    audio_in_some_exam=None,
    last_accessed_media=None,
):
    student = {
        "studentUuid": _STUDENT_UUID,
        "sessionUuid": _SESSION_UUID,
        "firstNames": "Maija",
        "lastName": "Meikäläinen",
        "studentBd": "010105",
        "studentStatus": "exam-in-progress",
        "sessionStatus": "exam_in_progress",
        "updateTime": None,
        "examFinishedAt": None,
        "examTitle": "Matematiikka",
    }
    if is_allowed_to_use_browser is not None:
        student["isAllowedToUseBrowser"] = is_allowed_to_use_browser
    if last_accessed_media is not None:
        student["lastAccessedMedia"] = last_accessed_media
    data = {"students": [student]}
    if audio_in_some_exam is not None:
        data["audioInSomeExam"] = audio_in_some_exam
    return [{"data": data}]


def test_invigilator_view_renders_student_without_uuid_columns(
    wui_client, override_session, mocker
):
    mocker.patch(
        "ktp_controller.api.client.get_raw_abitti2_stats_messages",
        return_value=_raw_abitti2_stats_messages(),
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.invigilator.view"}),
        )
    )

    response = wui_client.get("/invigilator/")

    assert response.status_code == 200
    assert "Maija Meikäläinen" in response.text
    assert "Student uuid" not in response.text
    assert "Session uuid" not in response.text


def test_invigilator_view_uses_session_locale(wui_client, override_session, mocker):
    mocker.patch(
        "ktp_controller.api.client.get_raw_abitti2_stats_messages",
        return_value=[],
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.invigilator.view"}),
            locale="en",
        )
    )

    response = wui_client.get("/invigilator/")

    assert response.status_code == 200
    assert '<html lang="en">' in response.text
    assert "Birthday" in response.text


def test_invigilator_view_locale_switcher_has_no_inline_script(
    wui_client, override_session, mocker
):
    # The page's CSP has no 'unsafe-inline' in script-src, so the
    # language switcher must not rely on an inline event-handler
    # attribute (e.g. onchange="..."), which browsers silently drop.
    mocker.patch(
        "ktp_controller.api.client.get_raw_abitti2_stats_messages",
        return_value=[],
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.invigilator.view"}),
        )
    )

    response = wui_client.get("/invigilator/")

    assert response.status_code == 200
    assert 'action="/locale"' in response.text
    assert "onchange=" not in response.text
    assert '<script src="/static/locale_switcher.js">' in response.text

    static_response = wui_client.get("/static/locale_switcher.js")
    assert static_response.status_code == 200


def test_invigilator_view_loads_vendored_htmx(wui_client, override_session, mocker):
    mocker.patch(
        "ktp_controller.api.client.get_raw_abitti2_stats_messages",
        return_value=[],
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.invigilator.view"}),
        )
    )

    response = wui_client.get("/invigilator/")

    assert response.status_code == 200
    assert '<script src="/static/htmx.min.js">' in response.text
    assert "unpkg.com" not in response.text

    static_response = wui_client.get("/static/htmx.min.js")
    assert static_response.status_code == 200


def test_invigilator_view_csp_has_no_unpkg(wui_client, override_session, mocker):
    mocker.patch(
        "ktp_controller.api.client.get_raw_abitti2_stats_messages",
        return_value=[],
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.invigilator.view"}),
        )
    )

    response = wui_client.get("/invigilator/")

    assert response.status_code == 200
    csp = response.headers["content-security-policy"]
    assert "unpkg.com" not in csp
    assert "script-src 'self';" in csp


def test_invigilator_view_forbidden_without_permission(wui_client, override_session):
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset(),
        )
    )

    response = wui_client.get("/invigilator/")

    assert response.status_code == 403


def test_invigilator_ws_rejects_without_session(wui_client, mocker):
    mocker.patch(
        "ktp_controller.wui.auth.get_current_session",
        side_effect=ktp_controller.wui.auth.NotAuthenticatedError,
    )

    with pytest.raises(starlette.testclient.WebSocketDisconnect) as exc_info:
        with wui_client.websocket_connect("/invigilator/ws"):
            pass

    assert exc_info.value.code == 4401


def test_invigilator_ws_rejects_without_permission(wui_client, mocker):
    mocker.patch(
        "ktp_controller.wui.auth.get_current_session",
        return_value=ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset(),
        ),
    )

    with pytest.raises(starlette.testclient.WebSocketDisconnect) as exc_info:
        with wui_client.websocket_connect("/invigilator/ws"):
            pass

    assert exc_info.value.code == 4403


def test_invigilator_ws_registers_and_unregisters(wui_client, mocker):
    mocker.patch(
        "ktp_controller.wui.auth.get_current_session",
        return_value=ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.invigilator.view"}),
        ),
    )
    register_mock = mocker.patch.object(
        ktp_controller.wui.main.APP.state.invigilator_ws_registry,
        "register",
        new=mocker.AsyncMock(),
    )
    unregister_mock = mocker.patch.object(
        ktp_controller.wui.main.APP.state.invigilator_ws_registry,
        "unregister",
        new=mocker.AsyncMock(),
    )

    with wui_client.websocket_connect("/invigilator/ws"):
        pass

    register_mock.assert_awaited_once()
    unregister_mock.assert_awaited_once()


def test_invigilator_view_shows_end_exam_button_with_permission(
    wui_client, override_session, mocker
):
    mocker.patch(
        "ktp_controller.api.client.get_raw_abitti2_stats_messages",
        return_value=_raw_abitti2_stats_messages(),
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.invigilator.view", "wui.actions.end-exam"}),
        )
    )

    response = wui_client.get("/invigilator/")

    assert response.status_code == 200
    assert 'hx-post="/actions/end-exam"' in response.text
    assert f'data-session-uuid="{_SESSION_UUID}"' in response.text
    assert f'data-student-uuid="{_STUDENT_UUID}"' in response.text
    assert "hx-confirm" not in response.text
    assert 'id="end-exam-confirm-overlay"' in response.text
    assert 'class="end-exam-confirm-yes"' in response.text
    assert 'class="end-exam-confirm-no"' in response.text


def test_invigilator_view_hides_end_exam_button_without_permission(
    wui_client, override_session, mocker
):
    mocker.patch(
        "ktp_controller.api.client.get_raw_abitti2_stats_messages",
        return_value=_raw_abitti2_stats_messages(),
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.invigilator.view"}),
        )
    )

    response = wui_client.get("/invigilator/")

    assert response.status_code == 200
    assert "/actions/end-exam" not in response.text


def test_invigilator_view_renders_question_marks_when_browser_permission_missing(
    wui_client, override_session, mocker
):
    mocker.patch(
        "ktp_controller.api.client.get_raw_abitti2_stats_messages",
        return_value=_raw_abitti2_stats_messages(),
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset(
                {
                    "wui.invigilator.view",
                    "wui.actions.set-exam-session-permission-to-use-browsers",
                }
            ),
        )
    )

    response = wui_client.get("/invigilator/")

    assert response.status_code == 200
    assert "???" in response.text
    assert "browser-permission-checkbox" not in response.text


def test_invigilator_view_renders_checked_browser_permission_checkbox(
    wui_client, override_session, mocker
):
    mocker.patch(
        "ktp_controller.api.client.get_raw_abitti2_stats_messages",
        return_value=_raw_abitti2_stats_messages(is_allowed_to_use_browser=True),
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset(
                {
                    "wui.invigilator.view",
                    "wui.actions.set-exam-session-permission-to-use-browsers",
                }
            ),
        )
    )

    response = wui_client.get("/invigilator/")

    assert response.status_code == 200
    assert 'class="browser-permission-checkbox"' in response.text
    assert "checked" in response.text
    assert "disabled" not in response.text
    assert (
        'hx-post="/actions/set-exam-session-permission-to-use-browsers"'
        in response.text
    )


def test_invigilator_view_renders_unchecked_browser_permission_checkbox(
    wui_client, override_session, mocker
):
    mocker.patch(
        "ktp_controller.api.client.get_raw_abitti2_stats_messages",
        return_value=_raw_abitti2_stats_messages(is_allowed_to_use_browser=False),
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset(
                {
                    "wui.invigilator.view",
                    "wui.actions.set-exam-session-permission-to-use-browsers",
                }
            ),
        )
    )

    response = wui_client.get("/invigilator/")

    assert response.status_code == 200
    assert 'class="browser-permission-checkbox"' in response.text
    assert "checked" not in response.text
    assert "disabled" not in response.text


def test_invigilator_view_disables_browser_permission_checkbox_without_permission(
    wui_client, override_session, mocker
):
    mocker.patch(
        "ktp_controller.api.client.get_raw_abitti2_stats_messages",
        return_value=_raw_abitti2_stats_messages(is_allowed_to_use_browser=True),
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.invigilator.view"}),
        )
    )

    response = wui_client.get("/invigilator/")

    assert response.status_code == 200
    assert 'class="browser-permission-checkbox"' in response.text
    assert "disabled" in response.text


def test_invigilator_view_hides_last_audio_column_when_no_audio_in_exam(
    wui_client, override_session, mocker
):
    mocker.patch(
        "ktp_controller.api.client.get_raw_abitti2_stats_messages",
        return_value=_raw_abitti2_stats_messages(audio_in_some_exam=False),
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset(
                {"wui.invigilator.view", "wui.actions.allow-audio-replay"}
            ),
            locale="en",
        )
    )

    response = wui_client.get("/invigilator/")

    assert response.status_code == 200
    assert "Last played audio" not in response.text
    assert "allow-audio-replay-button" not in response.text


def test_invigilator_view_shows_empty_cell_when_last_audio_is_zero(
    wui_client, override_session, mocker
):
    mocker.patch(
        "ktp_controller.api.client.get_raw_abitti2_stats_messages",
        return_value=_raw_abitti2_stats_messages(
            audio_in_some_exam=True, last_accessed_media=None
        ),
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset(
                {"wui.invigilator.view", "wui.actions.allow-audio-replay"}
            ),
            locale="en",
        )
    )

    response = wui_client.get("/invigilator/")

    assert response.status_code == 200
    assert "Last played audio" in response.text
    assert "allow-audio-replay-button" not in response.text


def test_invigilator_view_shows_allow_audio_replay_button_with_permission(
    wui_client, override_session, mocker
):
    mocker.patch(
        "ktp_controller.api.client.get_raw_abitti2_stats_messages",
        return_value=_raw_abitti2_stats_messages(
            audio_in_some_exam=True, last_accessed_media="3"
        ),
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset(
                {"wui.invigilator.view", "wui.actions.allow-audio-replay"}
            ),
            locale="en",
        )
    )

    response = wui_client.get("/invigilator/")

    assert response.status_code == 200
    assert "Last played audio" in response.text
    assert "Allow replaying audio 3" in response.text
    assert f'data-student-uuid="{_STUDENT_UUID}"' in response.text
    assert 'data-last-audio="3"' in response.text
    assert 'data-exam-title="Matematiikka"' in response.text
    assert "allow-audio-replay-confirm-overlay" in response.text


def test_invigilator_view_hides_allow_audio_replay_button_without_permission(
    wui_client, override_session, mocker
):
    mocker.patch(
        "ktp_controller.api.client.get_raw_abitti2_stats_messages",
        return_value=_raw_abitti2_stats_messages(
            audio_in_some_exam=True, last_accessed_media="3"
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

    response = wui_client.get("/invigilator/")

    assert response.status_code == 200
    # Column is still shown (data-driven), but the button itself is
    # permission-gated, like the "End exam" button.
    assert "Last played audio" in response.text
    assert "allow-audio-replay-button" not in response.text
