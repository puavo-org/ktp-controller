import datetime

import fastapi.testclient
import pytest

import ktp_controller.utils
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


def _status_report(
    *,
    ktp_controller_version="0.8.0rc10",
    abitti2_version="1.27.0",
    abitti2_domain="what-not.koe.abitti.net",
    abitti2_cert_expires_at="2099-01-01T00:00:00.000+0000",
    puavo_os_image_release="O2611 Broom",
    puavo_os_image_name="opinsys-os-opinsys-bookworm-2026-03-09-100004-amd64.img",
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
        },
    }


def test_landing_view_requires_login(wui_client):
    response = wui_client.get("/")

    assert response.status_code == 303
    assert response.headers["location"].startswith("/login")


def test_landing_view_htmx_requires_login_sends_hx_redirect(wui_client):
    response = wui_client.get("/", headers={"HX-Request": "true"})

    assert response.status_code == 200
    assert response.headers["HX-Redirect"].startswith("/login")


def test_landing_view_forbidden_without_permission(wui_client, override_session):
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset(),
            locale="en",
        )
    )

    response = wui_client.get("/")

    assert response.status_code == 403


def test_landing_view_allowed_with_permission(wui_client, override_session, mocker):
    mocker.patch(
        "ktp_controller.api.client.get_last_status_report",
        return_value=_status_report(),
    )
    mocker.patch(
        "ktp_controller.api.client.get_raw_abitti2_stats_messages",
        return_value=[],
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.landing.view"}),
            locale="en",
        )
    )

    response = wui_client.get("/")

    assert response.status_code == 200
    assert b"alice" in response.content
    assert "0.8.0rc10" in response.text
    assert "1.27.0" in response.text
    assert "1/1/99" in response.text
    assert 'class="value-warning"' not in response.text
    assert "O2611 Broom" in response.text
    assert (
        'title="opinsys-os-opinsys-bookworm-2026-03-09-100004-amd64.img"'
        in response.text
    )
    assert "what-not" in response.text


def test_landing_view_shows_placeholder_without_status_report(
    wui_client, override_session, mocker
):
    mocker.patch(
        "ktp_controller.api.client.get_last_status_report",
        return_value=None,
    )
    mocker.patch(
        "ktp_controller.api.client.get_raw_abitti2_stats_messages",
        return_value=[],
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.landing.view"}),
            locale="en",
        )
    )

    response = wui_client.get("/")

    assert response.status_code == 200
    assert "Not available yet." in response.text


def test_landing_view_shows_placeholder_without_abitti2_version(
    wui_client, override_session, mocker
):
    mocker.patch(
        "ktp_controller.api.client.get_last_status_report",
        return_value=_status_report(abitti2_version=None),
    )
    mocker.patch(
        "ktp_controller.api.client.get_raw_abitti2_stats_messages",
        return_value=[],
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.landing.view"}),
            locale="en",
        )
    )

    response = wui_client.get("/")

    assert response.status_code == 200
    assert "Not available yet." in response.text


def test_landing_view_shows_placeholder_without_abitti2_domain(
    wui_client, override_session, mocker
):
    mocker.patch(
        "ktp_controller.api.client.get_last_status_report",
        return_value=_status_report(abitti2_domain=None),
    )
    mocker.patch(
        "ktp_controller.api.client.get_raw_abitti2_stats_messages",
        return_value=[],
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.landing.view"}),
            locale="en",
        )
    )

    response = wui_client.get("/")

    assert response.status_code == 200
    assert "Not available yet." in response.text


def test_landing_view_shows_warning_for_soon_expiring_cert(
    wui_client, override_session, mocker
):
    mocker.patch(
        "ktp_controller.api.client.get_last_status_report",
        return_value=_status_report(
            abitti2_cert_expires_at=(
                ktp_controller.utils.utcnow() + datetime.timedelta(days=1)
            ).isoformat()
        ),
    )
    mocker.patch(
        "ktp_controller.api.client.get_raw_abitti2_stats_messages",
        return_value=[],
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.landing.view"}),
            locale="en",
        )
    )

    response = wui_client.get("/")

    assert response.status_code == 200
    assert 'class="value-warning"' in response.text


def test_landing_view_no_warning_for_cert_expiring_far_in_the_future(
    wui_client, override_session, mocker
):
    mocker.patch(
        "ktp_controller.api.client.get_last_status_report",
        return_value=_status_report(
            abitti2_cert_expires_at=(
                ktp_controller.utils.utcnow() + datetime.timedelta(days=30)
            ).isoformat()
        ),
    )
    mocker.patch(
        "ktp_controller.api.client.get_raw_abitti2_stats_messages",
        return_value=[],
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.landing.view"}),
            locale="en",
        )
    )

    response = wui_client.get("/")

    assert response.status_code == 200
    assert 'class="value-warning"' not in response.text


def test_landing_view_shows_question_marks_without_cert(
    wui_client, override_session, mocker
):
    mocker.patch(
        "ktp_controller.api.client.get_last_status_report",
        return_value=_status_report(abitti2_cert_expires_at=None),
    )
    mocker.patch(
        "ktp_controller.api.client.get_raw_abitti2_stats_messages",
        return_value=[],
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.landing.view"}),
            locale="en",
        )
    )

    response = wui_client.get("/")

    assert response.status_code == 200
    assert "???" in response.text
    assert 'class="value-warning"' not in response.text


def test_landing_view_shows_question_marks_without_os_release(
    wui_client, override_session, mocker
):
    mocker.patch(
        "ktp_controller.api.client.get_last_status_report",
        return_value=_status_report(puavo_os_image_release=None),
    )
    mocker.patch(
        "ktp_controller.api.client.get_raw_abitti2_stats_messages",
        return_value=[],
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.landing.view"}),
            locale="en",
        )
    )

    response = wui_client.get("/")

    assert response.status_code == 200
    assert "???" in response.text


def _raw_abitti2_stats_messages(statuses_and_connected):
    students = []
    for index, (status, is_connected) in enumerate(statuses_and_connected, start=1):
        students.append(
            {
                "studentUuid": f"{index:08d}-1111-1111-1111-111111111111",
                "sessionUuid": f"{index:08d}-2222-2222-2222-222222222222",
                "firstNames": f"Maija{index}",
                "lastName": "Meikäläinen",
                "studentBd": f"{index:02d}0105",
                "studentStatus": status,
                "sessionStatus": status.replace("-", "_"),
                "updateTime": None,
                "examFinishedAt": None,
                "isConnected": is_connected,
                "examTitle": "Matematiikka",
                "loginInitiatedOnBrowser": status.endswith("-browser"),
                "isAllowedToUseBrowser": False,
            }
        )
    return [{"data": {"students": students}}]


def test_landing_view_renders_student_state_counts(
    wui_client, override_session, mocker
):
    mocker.patch(
        "ktp_controller.api.client.get_last_status_report",
        return_value=_status_report(),
    )
    mocker.patch(
        "ktp_controller.api.client.get_raw_abitti2_stats_messages",
        return_value=_raw_abitti2_stats_messages(
            [
                ("in-exam-browser", True),
                ("waiting-for-auth-browser", True),
                ("exam-finished-by-supo", True),
                ("in-exam-browser", False),
            ]
        ),
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.landing.view"}),
            locale="en",
        )
    )

    response = wui_client.get("/")

    assert response.status_code == 200
    assert response.text.count('id="student-state-counts"') == 1
    assert '<span class="pill pill-has_problems">Has problems 1</span>' in (
        response.text
    )
    assert '<span class="pill pill-in_exam">In exam 1</span>' in response.text
    assert '<span class="pill pill-finished">Finished 1</span>' in response.text
    assert '<span class="pill pill-waiting">Waiting 1</span>' in response.text


def test_landing_view_student_state_counts_present_in_htmx_partial(
    wui_client, override_session, mocker
):
    mocker.patch(
        "ktp_controller.api.client.get_last_status_report",
        return_value=_status_report(),
    )
    mocker.patch(
        "ktp_controller.api.client.get_raw_abitti2_stats_messages",
        return_value=_raw_abitti2_stats_messages([("in-exam-browser", True)]),
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.landing.view"}),
            locale="en",
        )
    )

    response = wui_client.get("/", headers={"HX-Request": "true"})

    assert response.status_code == 200
    assert "<html" not in response.text
    assert 'id="student-state-counts"' in response.text
    assert "hx-swap-oob" not in response.text
    assert '<span class="pill pill-in_exam">In exam 1</span>' in response.text


def test_landing_ws_route_reachable_with_landing_permission_only(wui_client, mocker):
    mocker.patch(
        "ktp_controller.wui.auth.get_current_session",
        return_value=ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.landing.view"}),
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


def test_landing_view_honors_forwarded_prefix(wui_client, override_session, mocker):
    mocker.patch(
        "ktp_controller.api.client.get_last_status_report",
        return_value=_status_report(),
    )
    mocker.patch(
        "ktp_controller.api.client.get_raw_abitti2_stats_messages",
        return_value=[],
    )
    override_session(
        ktp_controller.wui.auth.Session(
            session_id="test-session",
            username="alice",
            permissions=frozenset({"wui.landing.view"}),
            locale="en",
        )
    )

    response = wui_client.get(
        "/remote/12345/", headers={"X-Forwarded-Prefix": "/remote/12345"}
    )

    assert response.status_code == 200
    assert b'href="/remote/12345/static/app.css"' in response.content
    assert b'action="/remote/12345/logout"' in response.content
