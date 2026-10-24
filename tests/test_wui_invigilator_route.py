import datetime
import itertools
import re

import fastapi.testclient
import pytest
import starlette.testclient

import ktp_controller.wui.auth
import ktp_controller.wui.main


def _browser_permission_checkbox_tag(html):
    match = re.search(
        r'<input[^>]*class="browser-permission-checkbox"[^>]*>', html, re.DOTALL
    )
    assert match, "browser-permission-checkbox input not found in response"
    return match.group(0)


def _end_exam_button_tag(html):
    match = re.search(r'<button[^>]*class="end-exam-button"[^>]*>', html, re.DOTALL)
    assert match, "end-exam-button button not found in response"
    return match.group(0)


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


def test_invigilator_view_htmx_requires_login_sends_hx_redirect(wui_client):
    response = wui_client.get("/invigilator/", headers={"HX-Request": "true"})

    assert response.status_code == 200
    assert response.headers["HX-Redirect"].startswith("/login")


def test_invigilator_view_allowed_with_permission(wui_client, override_session, mocker):
    _mock_abitti2_state(mocker, is_empty=True)
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


def test_invigilator_view_honors_forwarded_prefix(wui_client, override_session, mocker):
    _mock_abitti2_state(mocker, is_empty=True)
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.invigilator.view"}),
        )
    )

    response = wui_client.get(
        "/remote/12345/invigilator/", headers={"X-Forwarded-Prefix": "/remote/12345"}
    )

    assert response.status_code == 200
    assert b'href="/remote/12345/static/app.css"' in response.content
    assert b'action="/remote/12345/logout"' in response.content
    assert b'data-prefix="/remote/12345"' in response.content
    assert b'aria-current="page"' in response.content


def test_invigilator_view_shows_user_menu_dropdown(
    wui_client, override_session, mocker
):
    _mock_abitti2_state(mocker, is_empty=True)
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.invigilator.view"}),
        )
    )

    response = wui_client.get("/invigilator/")

    assert response.status_code == 200
    assert '<details class="dropdown">' in response.text
    assert "<summary>🇫🇮 alice</summary>" in response.text
    assert "Logged in as" not in response.text
    assert 'action="/logout"' in response.text
    assert 'action="/locale"' in response.text


def test_invigilator_view_shows_student_access_code_nav_link(
    wui_client, override_session, mocker
):
    _mock_abitti2_state(mocker, is_empty=True)
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
    _mock_abitti2_state(mocker, is_empty=True)
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


def _raw_abitti2_stats_messages(
    *,
    student_count: int,
    is_allowed_to_use_browser: bool,
    audio_in_some_exam: bool | None,
    last_accessed_media: str | None,
    student_statuses: list[str],
    update_time: str | None,
    exam_titles: list[str | None],
    is_connecteds: [bool],
):
    if student_count > 28:
        raise ValueError("student_count cannot be more than 28")
    if student_count < 0:
        raise ValueError("student_count cannot be less than 0")

    students = []

    exam_title_iter = itertools.cycle(exam_titles)
    student_status_iter = itertools.cycle(student_statuses)
    is_connected_iter = itertools.cycle(is_connecteds)

    for index in range(student_count):
        index += 1
        exam_title = next(exam_title_iter)
        student_status = next(student_status_iter)
        is_connected = next(is_connected_iter)
        student = {
            "studentUuid": f"{index:08d}-1111-1111-1111-111111111111",
            "sessionUuid": f"{index:08d}-2222-2222-2222-222222222222",
            "firstNames": f"Maija{index}",
            "lastName": "Meikäläinen",
            "studentBd": f"{index:02d}0105",
            "studentStatus": student_status,
            "sessionStatus": student_status.replace("-", "_"),
            "updateTime": update_time,
            "examFinishedAt": None,
            "isConnected": is_connected,
            "examTitle": exam_title,
            "loginInitiatedOnBrowser": student_status.endswith("-browser")
            or is_allowed_to_use_browser,
            "isAllowedToUseBrowser": is_allowed_to_use_browser,
        }
        if last_accessed_media is not None:
            student["lastAccessedMedia"] = last_accessed_media
        students.append(student)
    data = {"students": students}
    if audio_in_some_exam is not None:
        data["audioInSomeExam"] = audio_in_some_exam
    return [{"data": data}]


def _decrypted_exams(
    *, exam_titles: [str], start_time: datetime.datetime | None = None
):
    if start_time is not None and start_time.tzinfo != datetime.UTC:
        raise ValueError("start_time must be UTC")
    exams = []
    for index, exam_title in enumerate(exam_titles):
        index += 1
        exams.append(
            {
                "examUuid": f"{index:08d}-3333-3333-3333-333333333333",
                "examTitle": exam_title,
                "hasStarted": start_time is not None,
                "startTime": None
                if start_time is None
                else start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "type": "xml",
            }
        )

    return exams


def _mock_abitti2_state(
    mocker,
    /,
    *,
    student_count: int = 1,
    is_empty: bool = False,
    is_allowed_to_use_browser: bool = False,
    audio_in_some_exam=None,
    last_accessed_media=None,
    student_statuses: list[str] | None = None,
    update_time=None,
    exam_titles: list[str] | None = None,
    is_connecteds: list[bool] | None = None,
    student_exam_titles: list[str | None] | None = None,
):
    if exam_titles is None:
        exam_titles = ["Matematiikka"]

    if student_statuses is None:
        student_statuses = ["in-exam-browser"]

    if is_connecteds is None:
        is_connecteds = [True]

    if student_exam_titles is None:
        student_exam_titles = list(exam_titles)

    mocker.patch(
        "ktp_controller.api.client.get_raw_abitti2_stats_messages",
        return_value=[]
        if is_empty
        else _raw_abitti2_stats_messages(
            student_count=student_count,
            is_allowed_to_use_browser=is_allowed_to_use_browser,
            audio_in_some_exam=audio_in_some_exam,
            last_accessed_media=last_accessed_media,
            student_statuses=student_statuses,
            update_time=update_time,
            exam_titles=student_exam_titles,
            is_connecteds=is_connecteds,
        ),
    )
    mocker.patch(
        "ktp_controller.abitti2.client.get_decrypted_exams",
        return_value=[] if is_empty else _decrypted_exams(exam_titles=exam_titles),
    )


def test_invigilator_view_renders_student_without_uuid_columns(
    wui_client, override_session, mocker
):
    _mock_abitti2_state(mocker)
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.invigilator.view"}),
        )
    )

    response = wui_client.get("/invigilator/")

    assert response.status_code == 200
    assert "Maija1 Meikäläinen" in response.text
    assert "Student uuid" not in response.text
    assert "Session uuid" not in response.text


def test_invigilator_view_uses_session_locale(wui_client, override_session, mocker):
    _mock_abitti2_state(mocker, is_empty=True)
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
    assert '<html lang="en" data-prefix="">' in response.text
    assert ">No exams</p>" in response.text


def test_invigilator_view_formats_birthday_as_ddmmyy_regardless_of_locale(
    wui_client, override_session, mocker
):
    _mock_abitti2_state(mocker)
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
    assert "<td>010105</td>" in response.text


def test_invigilator_view_locale_switcher_has_no_inline_script(
    wui_client, override_session, mocker
):
    # The page's CSP has no 'unsafe-inline' in script-src, so the
    # language switcher must not rely on an inline event-handler
    # attribute (e.g. onchange="..."), which browsers silently drop.
    _mock_abitti2_state(mocker, is_empty=True)
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
    _mock_abitti2_state(mocker, is_empty=True)
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
    _mock_abitti2_state(mocker, is_empty=True)
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
    _mock_abitti2_state(mocker)
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
    assert 'data-session-uuid="00000001-2222-2222-2222-222222222222"' in response.text
    assert 'data-student-uuid="00000001-1111-1111-1111-111111111111"' in response.text
    assert "hx-confirm" not in response.text
    assert 'id="end-exam-confirm-overlay"' in response.text
    assert 'class="end-exam-confirm-yes"' in response.text
    assert 'class="end-exam-confirm-no"' in response.text


def test_invigilator_view_hides_end_exam_button_without_permission(
    wui_client, override_session, mocker
):
    _mock_abitti2_state(mocker)
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


def test_invigilator_view_enables_end_exam_button_for_in_exam_student(
    wui_client, override_session, mocker
):
    _mock_abitti2_state(mocker)
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.invigilator.view", "wui.actions.end-exam"}),
        )
    )

    response = wui_client.get("/invigilator/")

    assert response.status_code == 200
    assert "disabled" not in _end_exam_button_tag(response.text)


def test_invigilator_view_enables_end_exam_button_for_idle_student(
    wui_client, override_session, mocker
):
    idle_update_time = (
        datetime.datetime.now(datetime.UTC) - datetime.timedelta(minutes=31)
    ).isoformat()
    _mock_abitti2_state(mocker, update_time=idle_update_time)
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.invigilator.view", "wui.actions.end-exam"}),
            locale="en",
        )
    )

    response = wui_client.get("/invigilator/")

    assert response.status_code == 200
    assert '<span class="pill pill-has_problems">Idle</span>' in response.text
    assert "disabled" not in _end_exam_button_tag(response.text)


def test_invigilator_view_disables_end_exam_button_for_finished_student(
    wui_client, override_session, mocker
):
    _mock_abitti2_state(mocker, student_statuses=["session-ended"])
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.invigilator.view", "wui.actions.end-exam"}),
        )
    )

    response = wui_client.get("/invigilator/")

    assert response.status_code == 200
    assert "disabled" in _end_exam_button_tag(response.text)


def test_invigilator_view_disables_end_exam_button_for_student_with_other_flags(
    wui_client, override_session, mocker
):
    _mock_abitti2_state(mocker, is_connecteds=[False])
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.invigilator.view", "wui.actions.end-exam"}),
            locale="en",
        )
    )

    response = wui_client.get("/invigilator/")

    assert response.status_code == 200
    assert '<span class="pill pill-has_problems">Disconnected</span>' in response.text
    assert "disabled" in _end_exam_button_tag(response.text)


def test_invigilator_view_renders_empty_when_user_does_not_want_to_use_browser(
    wui_client, override_session, mocker
):
    _mock_abitti2_state(mocker, student_statuses=["in-exam"])
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
    assert "browser-permission-checkbox" not in response.text


def test_invigilator_view_renders_checked_browser_permission_checkbox(
    wui_client, override_session, mocker
):
    _mock_abitti2_state(mocker, is_allowed_to_use_browser=True)
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
    checkbox_tag = _browser_permission_checkbox_tag(response.text)
    assert "checked" in checkbox_tag
    assert "disabled" not in checkbox_tag
    assert (
        'hx-post="/actions/set-exam-session-permission-to-use-browsers"'
        in response.text
    )


def test_invigilator_view_renders_unchecked_browser_permission_checkbox(
    wui_client, override_session, mocker
):
    _mock_abitti2_state(mocker, is_allowed_to_use_browser=False)
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
    checkbox_tag = _browser_permission_checkbox_tag(response.text)
    assert "checked" not in checkbox_tag
    assert "disabled" not in checkbox_tag


def test_invigilator_view_disables_browser_permission_checkbox_without_permission(
    wui_client, override_session, mocker
):
    _mock_abitti2_state(mocker, is_allowed_to_use_browser=True)
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.invigilator.view"}),
        )
    )

    response = wui_client.get("/invigilator/")

    assert response.status_code == 200
    checkbox_tag = _browser_permission_checkbox_tag(response.text)
    assert "disabled" in checkbox_tag


def test_invigilator_view_disables_browser_permission_checkbox_for_finished_student(
    wui_client, override_session, mocker
):
    _mock_abitti2_state(
        mocker, is_allowed_to_use_browser=True, student_statuses=["session-ended"]
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
    checkbox_tag = _browser_permission_checkbox_tag(response.text)
    assert "disabled" in checkbox_tag


def test_invigilator_view_hides_last_audio_column_when_no_audio_in_exam(
    wui_client, override_session, mocker
):
    _mock_abitti2_state(mocker, audio_in_some_exam=False)
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
    _mock_abitti2_state(mocker, audio_in_some_exam=True, last_accessed_media=None)
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
    _mock_abitti2_state(mocker, audio_in_some_exam=True, last_accessed_media="3")
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
    assert 'data-student-uuid="00000001-1111-1111-1111-111111111111"' in response.text
    assert 'data-last-audio="3"' in response.text
    assert 'data-exam-title="Matematiikka"' in response.text
    assert "allow-audio-replay-confirm-overlay" in response.text


def test_invigilator_view_hides_allow_audio_replay_button_without_permission(
    wui_client, override_session, mocker
):
    _mock_abitti2_state(mocker, audio_in_some_exam=True, last_accessed_media="3")
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


def test_invigilator_view_renders_student_state_counts(
    wui_client, override_session, mocker
):
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

    response = wui_client.get("/invigilator/")

    assert response.status_code == 200
    # Exactly once: the full page includes the counts once via the
    # common header and once via the table partial, which must only
    # emit them for htmx requests to avoid rendering duplicate
    # #student-state-counts elements.
    assert response.text.count('id="student-state-counts"') == 1
    assert '<span class="pill pill-has_problems">Has problems 1</span>' in (
        response.text
    )
    assert '<span class="pill pill-in_exam">In exam 1</span>' in response.text
    assert '<span class="pill pill-finished">Finished 1</span>' in response.text
    assert '<span class="pill pill-waiting">Waiting 1</span>' in response.text


def test_invigilator_view_student_state_counts_ignore_name_birthday_filter(
    wui_client, override_session, mocker
):
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
        "/invigilator/", params={"name_birthday_filter": "Maija1"}
    )

    assert response.status_code == 200
    assert "Maija1 Meikäläinen" in response.text
    assert "Maija2 Meikäläinen" not in response.text
    assert "Maija3 Meikäläinen" not in response.text
    assert "Maija4 Meikäläinen" not in response.text
    assert '<span class="pill pill-has_problems">Has problems 1</span>' in (
        response.text
    )
    assert '<span class="pill pill-in_exam">In exam 1</span>' in response.text
    assert '<span class="pill pill-finished">Finished 1</span>' in response.text
    assert '<span class="pill pill-waiting">Waiting 1</span>' in response.text


def test_invigilator_view_renders_student_list_table_state_pills(
    wui_client, override_session, mocker
):
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

    response = wui_client.get("/invigilator/")

    assert response.status_code == 200
    assert '<span class="pill pill-in_exam">In exam</span>' in response.text
    assert '<span class="pill pill-finished">Finished</span>' in response.text
    assert '<span class="pill pill-has_problems">Disconnected</span>' in response.text
    assert '<span class="pill pill-waiting">Waiting</span>' in response.text


def test_invigilator_view_renders_student_list_table_state_pills_in_htmx_partial(
    wui_client, override_session, mocker
):
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

    response = wui_client.get("/invigilator/", headers={"HX-Request": "true"})

    assert response.status_code == 200
    assert '<span class="pill pill-in_exam">In exam</span>' in response.text
    assert '<span class="pill pill-finished">Finished</span>' in response.text
    assert '<span class="pill pill-has_problems">Disconnected</span>' in response.text
    assert '<span class="pill pill-waiting">Waiting</span>' in response.text


def test_invigilator_view_student_state_counts_present_in_htmx_partial(
    wui_client, override_session, mocker
):
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

    response = wui_client.get("/invigilator/", headers={"HX-Request": "true"})

    assert response.status_code == 200
    assert 'id="student-state-counts" hx-swap-oob="true"' in response.text
    assert '<span class="pill pill-has_problems">Has problems 1</span>' in (
        response.text
    )
    assert '<span class="pill pill-in_exam">In exam 1</span>' in response.text
    assert '<span class="pill pill-finished">Finished 1</span>' in response.text
    assert '<span class="pill pill-waiting">Waiting 1</span>' in response.text


def _exam_group_html(html, exam_title):
    match = re.search(
        rf'<details class="exam-group[^"]*" data-exam-title="{re.escape(exam_title)}"[^>]*>.*?</details>',
        html,
        re.DOTALL,
    )
    assert match, f"exam-group block for {exam_title!r} not found"
    return match.group(0)


def test_invigilator_view_renders_exam_specific_student_state_counts(
    wui_client, override_session, mocker
):
    _mock_abitti2_state(
        mocker,
        student_count=4,
        exam_titles=["Matematiikka", "Englanti"],
        student_statuses=[
            "in-exam-browser",
            "exam-finished-by-supo",
            "in-exam-browser",
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

    response = wui_client.get("/invigilator/")

    assert response.status_code == 200
    matematiikka_html = _exam_group_html(response.text, "Matematiikka")
    assert '<span class="pill pill-in_exam">In exam 2</span>' in matematiikka_html
    assert '<span class="pill pill-finished">Finished 0</span>' in matematiikka_html
    assert (
        '<span class="pill pill-has_problems">Has problems 0</span>'
        in matematiikka_html
    )

    englanti_html = _exam_group_html(response.text, "Englanti")
    assert '<span class="pill pill-in_exam">In exam 0</span>' in englanti_html
    assert '<span class="pill pill-finished">Finished 1</span>' in englanti_html
    assert '<span class="pill pill-has_problems">Has problems 1</span>' in englanti_html


def test_invigilator_view_unknown_exam_group_shows_own_student_state_counts(
    wui_client, override_session, mocker
):
    _mock_abitti2_state(mocker, student_exam_titles=[None])
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
    unknown_html = _exam_group_html(response.text, "???")
    # A student with no exam title gets an "undefined exam" flag, which
    # puts them in HAS_PROBLEMS regardless of their raw studentStatus.
    assert '<span class="pill pill-has_problems">Has problems 1</span>' in (
        unknown_html
    )


def test_invigilator_view_exam_specific_student_state_counts_follow_name_birthday_filter(
    wui_client, override_session, mocker
):
    _mock_abitti2_state(
        mocker,
        student_count=4,
        exam_titles=["Matematiikka", "Englanti"],
        student_statuses=[
            "in-exam-browser",
            "exam-finished-by-supo",
            "in-exam-browser",
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

    # Narrow down to the single "Maija1" (Matematiikka, in exam) student.
    # Unlike the global header pills (which ignore this filter, see
    # test_invigilator_view_student_state_counts_ignore_name_birthday_filter),
    # the per-exam pills must follow it.
    response = wui_client.get(
        "/invigilator/", params={"name_birthday_filter": "Maija1"}
    )

    assert response.status_code == 200
    matematiikka_html = _exam_group_html(response.text, "Matematiikka")
    assert '<span class="pill pill-in_exam">In exam 1</span>' in matematiikka_html
    assert '<span class="pill pill-finished">Finished 0</span>' in matematiikka_html

    englanti_html = _exam_group_html(response.text, "Englanti")
    assert '<span class="pill pill-in_exam">In exam 0</span>' in englanti_html
    assert '<span class="pill pill-finished">Finished 0</span>' in englanti_html
    assert '<span class="pill pill-has_problems">Has problems 0</span>' in englanti_html

    # The global header pills, by contrast, still show the unfiltered totals.
    assert '<span class="pill pill-in_exam">In exam 2</span>' in response.text
    assert '<span class="pill pill-finished">Finished 1</span>' in response.text


def test_invigilator_view_exam_specific_student_state_counts_present_in_htmx_partial(
    wui_client, override_session, mocker
):
    _mock_abitti2_state(
        mocker,
        student_count=4,
        exam_titles=["Matematiikka", "Englanti"],
        student_statuses=[
            "in-exam-browser",
            "exam-finished-by-supo",
            "in-exam-browser",
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

    response = wui_client.get("/invigilator/", headers={"HX-Request": "true"})

    assert response.status_code == 200
    matematiikka_html = _exam_group_html(response.text, "Matematiikka")
    assert '<span class="pill pill-in_exam">In exam 2</span>' in matematiikka_html

    englanti_html = _exam_group_html(response.text, "Englanti")
    assert '<span class="pill pill-finished">Finished 1</span>' in englanti_html


def test_invigilator_view_groups_students_by_exam_title(
    wui_client, override_session, mocker
):
    _mock_abitti2_state(
        mocker, student_count=2, exam_titles=["Matematiikka", "Englanti"]
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
    assert response.text.count('<details class="exam-group" data-exam-title=') == 2
    assert '<details class="exam-group" data-exam-title="Matematiikka" open>' in (
        response.text
    )
    assert '<details class="exam-group" data-exam-title="Englanti" open>' in (
        response.text
    )
    assert "<h3>Matematiikka</h3>" in response.text
    assert "<h3>Englanti</h3>" in response.text
    assert "Exam title" not in response.text


def test_invigilator_view_collapses_exam_group_with_no_students_by_default(
    wui_client, override_session, mocker
):
    _mock_abitti2_state(
        mocker,
        student_count=1,
        exam_titles=["Matematiikka", "Englanti"],
        student_exam_titles=["Matematiikka"],
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
    assert '<details class="exam-group" data-exam-title="Matematiikka" open>' in (
        response.text
    )
    assert '<details class="exam-group" data-exam-title="Englanti" >' in response.text
    assert '<details class="exam-group" data-exam-title="Englanti" open>' not in (
        response.text
    )


def test_invigilator_view_collapses_exam_group_with_all_students_finished_by_default(
    wui_client, override_session, mocker
):
    _mock_abitti2_state(
        mocker,
        student_count=2,
        exam_titles=["Matematiikka", "Englanti"],
        student_exam_titles=["Matematiikka", "Englanti"],
        student_statuses=["in-exam-browser", "session-ended"],
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
    assert '<details class="exam-group" data-exam-title="Matematiikka" open>' in (
        response.text
    )
    assert '<details class="exam-group" data-exam-title="Englanti" >' in response.text
    assert '<details class="exam-group" data-exam-title="Englanti" open>' not in (
        response.text
    )


def test_invigilator_view_groups_student_with_missing_exam_title_as_question_marks(
    wui_client, override_session, mocker
):
    _mock_abitti2_state(mocker, student_exam_titles=[None])
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
    assert "<h3>???</h3>" in response.text


def test_invigilator_view_shows_no_students_row_with_headers_when_list_empty(
    wui_client, override_session, mocker
):
    _mock_abitti2_state(mocker, is_empty=True)
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
    assert response.text.count("<table") == 0
    assert '<details class="exam-group"' not in response.text
    assert "No exams" in response.text


def test_invigilator_view_shows_no_students_matching_filter_message(
    wui_client, override_session, mocker
):
    _mock_abitti2_state(mocker)
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.invigilator.view"}),
            locale="en",
        )
    )

    response = wui_client.get(
        "/invigilator/", params={"name_birthday_filter": "Nonexistent"}
    )

    assert response.status_code == 200
    assert response.text.count("<table") == 1
    assert (
        '<details class="exam-group" data-exam-title="Matematiikka" open>'
        in response.text
    )
    assert "No students matching 'Nonexistent'" in response.text


def test_invigilator_view_shows_expand_collapse_all_button(
    wui_client, override_session, mocker
):
    _mock_abitti2_state(mocker, exam_titles=["Matematiikka"])
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
    assert 'id="toggle-exam-groups-button"' in response.text
    assert 'data-expand-label="Expand all"' in response.text
    assert 'data-collapse-label="Collapse all"' in response.text
    assert ">Collapse all</button>" in response.text
    assert (
        "disabled"
        not in response.text.split('id="toggle-exam-groups-button"')[1].split(">")[0]
    )
    assert '<script src="/static/toggle_exam_groups.js">' in response.text

    static_response = wui_client.get("/static/toggle_exam_groups.js")
    assert static_response.status_code == 200


def test_invigilator_view_shows_expand_all_label_when_all_exam_groups_collapsed(
    wui_client, override_session, mocker
):
    _mock_abitti2_state(
        mocker, exam_titles=["Matematiikka"], student_statuses=["session-ended"]
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
    assert '<details class="exam-group" data-exam-title="Matematiikka" >' in (
        response.text
    )
    assert ">Expand all</button>" in response.text


def test_invigilator_view_disables_expand_collapse_all_button_when_no_students(
    wui_client, override_session, mocker
):
    _mock_abitti2_state(mocker, is_empty=True)
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
    button_tag = response.text.split('id="toggle-exam-groups-button"')[1].split(">")[0]
    assert "disabled" in button_tag


def test_invigilator_view_loads_preserve_exam_group_state_script(
    wui_client, override_session, mocker
):
    _mock_abitti2_state(mocker, is_empty=True)
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
    assert '<script src="/static/preserve_exam_group_state.js">' in response.text

    static_response = wui_client.get("/static/preserve_exam_group_state.js")
    assert static_response.status_code == 200


def test_invigilator_view_sortable_columns_and_filter_target_student_list_groups(
    wui_client, override_session, mocker
):
    _mock_abitti2_state(mocker)
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
    assert 'id="student-list-groups"' in response.text
    # 1 from the name/birthday filter input, 4 from the sortable columns
    # (name, birthday, state, last changed at).
    assert response.text.count('hx-target="#student-list-groups"') == 5
