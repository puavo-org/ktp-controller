import datetime

import pytest

import ktp_controller.utils
import ktp_controller.wui.auth
import ktp_controller.wui.main
from ktp_controller import WORKDIR
from tests.html_helpers import _header_tag, _nav_item_tag


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


def test_landing_view_allowed_with_permission(
    wui_client, override_session, mocker, make_status_report
):
    mocker.patch(
        "ktp_controller.api.client.get_last_status_report",
        return_value=make_status_report(),
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
    assert 'id="controller-info-header"' in response.text
    assert (
        'id="controller-info-header-icon" class="severity-icon" hidden' in response.text
    )
    assert 'id="controller-started-at-cell"' in response.text
    assert (
        'id="controller-started-at-icon" class="severity-icon" hidden' in response.text
    )
    assert 'id="controller-started-at"' in response.text
    assert 'data-started-at="2026-05-03T16:28:51.975000+00:00"' in response.text
    assert 'data-seconds-one="{n} second ago"' in response.text
    assert 'data-seconds-other="{n} seconds ago"' in response.text
    assert 'data-minutes-one="{n} minute ago"' in response.text
    assert 'data-minutes-other="{n} minutes ago"' in response.text
    assert 'data-hours-one="{n} hour ago"' in response.text
    assert 'data-hours-other="{n} hours ago"' in response.text
    assert 'data-days-one="{n} day ago"' in response.text
    assert 'data-days-other="{n} days ago"' in response.text
    assert "static/controller_started_at.js" in response.text
    assert "1/1/99" in response.text
    assert 'data-tooltip="1/1/99, 12:00\u202fAM"' in response.text
    assert 'class="value-warning"' not in response.text
    assert "O2611 Broom" in response.text
    assert (
        'data-tooltip="opinsys-os-opinsys-bookworm-2026-03-09-100004-amd64.img"'
        in response.text
    )
    assert "ktp-controller-test" in response.text
    assert "what-not" in response.text
    assert "static/page_refreshed_status.js" in response.text
    assert 'id="page-refreshed-status"' in response.text
    assert 'data-template-one="Page refreshed {n} second ago"' in response.text
    assert 'data-template-other="Page refreshed {n} seconds ago"' in response.text


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
    wui_client, override_session, mocker, make_status_report
):
    mocker.patch(
        "ktp_controller.api.client.get_last_status_report",
        return_value=make_status_report(abitti2_version=None),
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
    wui_client, override_session, mocker, make_status_report
):
    mocker.patch(
        "ktp_controller.api.client.get_last_status_report",
        return_value=make_status_report(abitti2_domain=None),
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
    wui_client, override_session, mocker, make_status_report
):
    mocker.patch(
        "ktp_controller.api.client.get_last_status_report",
        return_value=make_status_report(
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
    abitti2_header = _header_tag(response.text, "Abitti2")
    assert 'class="value-warning"' in abitti2_header
    assert "severity-icon" in abitti2_header
    controller_header = _header_tag(response.text, "Controller info")
    assert "value-warning" not in controller_header
    host_header = _header_tag(response.text, "Host system")
    assert "value-warning" not in host_header
    nav_item = _nav_item_tag(response.text, "Exam server")
    assert "value-warning" in nav_item
    assert "severity-icon" in nav_item


@pytest.mark.parametrize(
    ("delta", "expected_caption"),
    [
        pytest.param(
            datetime.timedelta(days=5, hours=12), "5 days left", id="days_left"
        ),
        pytest.param(
            datetime.timedelta(hours=5, minutes=30),
            "5 hours left",
            id="hours_left_within_a_day",
        ),
        pytest.param(-datetime.timedelta(hours=1), "Expired", id="already_expired"),
    ],
)
def test_landing_view_shows_cert_expiry_caption(
    wui_client, override_session, mocker, make_status_report, delta, expected_caption
):
    mocker.patch(
        "ktp_controller.api.client.get_last_status_report",
        return_value=make_status_report(
            abitti2_cert_expires_at=(ktp_controller.utils.utcnow() + delta).isoformat()
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
    assert (
        f'<small class="severity-caption">{expected_caption}</small>' in response.text
    )


def test_landing_view_no_warning_for_cert_expiring_far_in_the_future(
    wui_client, override_session, mocker, make_status_report
):
    mocker.patch(
        "ktp_controller.api.client.get_last_status_report",
        return_value=make_status_report(
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
    assert "severity-caption" not in response.text
    for title in ("Abitti2", "Host system"):
        header = _header_tag(response.text, title)
        assert "value-warning" not in header
        assert "value-error" not in header
        assert "severity-icon" not in header
    controller_header = _header_tag(response.text, "Controller info")
    assert "value-warning" not in controller_header
    assert "value-error" not in controller_header
    assert 'class="severity-icon" hidden' in controller_header
    nav_item = _nav_item_tag(response.text, "Exam server")
    assert "value-warning" not in nav_item
    assert "value-error" not in nav_item
    assert "severity-icon" not in nav_item
    assert 'hx-get="/nav_status"' in nav_item
    assert 'hx-trigger="live-update from:body throttle:2s"' in nav_item


def test_landing_view_shows_question_marks_without_cert(
    wui_client, override_session, mocker, make_status_report
):
    mocker.patch(
        "ktp_controller.api.client.get_last_status_report",
        return_value=make_status_report(abitti2_cert_expires_at=None),
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


def test_landing_view_shows_question_marks_without_host_release(
    wui_client, override_session, mocker, make_status_report
):
    mocker.patch(
        "ktp_controller.api.client.get_last_status_report",
        return_value=make_status_report(puavo_os_image_release=None),
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


def test_landing_view_shows_question_marks_without_hostname(
    wui_client, override_session, mocker, make_status_report
):
    mocker.patch(
        "ktp_controller.api.client.get_last_status_report",
        return_value=make_status_report(hostname=None),
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


@pytest.mark.parametrize(
    ("free_bytes", "expected_label", "expected_severity"),
    [
        pytest.param(100 * 1024**2 - 1, "Critical", "error", id="just_below_critical"),
        pytest.param(100 * 1024**2, "Low", "warning", id="at_critical_threshold"),
        pytest.param(3 * 1024**3 - 1, "Low", "warning", id="just_below_low"),
        pytest.param(3 * 1024**3, "Moderate", None, id="at_low_threshold"),
        pytest.param(10 * 1024**3 - 1, "Moderate", None, id="just_below_moderate"),
        pytest.param(10 * 1024**3, "Plenty", None, id="at_moderate_threshold"),
    ],
)
def test_landing_view_shows_free_disk_space_stage(
    wui_client,
    override_session,
    mocker,
    make_status_report,
    free_bytes,
    expected_label,
    expected_severity,
):
    mocker.patch(
        "ktp_controller.api.client.get_last_status_report",
        return_value=make_status_report(
            disk_usage=[{"dirpath": WORKDIR, "free": free_bytes}]
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
    host_header = _header_tag(response.text, "Host system")
    assert f">{expected_label}<" in response.text
    if expected_severity is None:
        assert "value-warning" not in host_header
        assert "value-error" not in host_header
    else:
        assert f'class="value-{expected_severity}"' in host_header


@pytest.mark.parametrize(
    ("disk_usage"),
    [
        pytest.param(None, id="disk_usage_missing"),
        pytest.param([], id="disk_usage_empty"),
        pytest.param([{"dirpath": "/", "free": 50 * 1024**3}], id="no_home_entry"),
    ],
)
def test_landing_view_shows_question_marks_without_home_disk_usage(
    wui_client, override_session, mocker, make_status_report, disk_usage
):
    mocker.patch(
        "ktp_controller.api.client.get_last_status_report",
        return_value=make_status_report(disk_usage=disk_usage),
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
    host_header = _header_tag(response.text, "Host system")
    assert 'class="value-error"' in host_header


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
    wui_client, override_session, mocker, make_status_report
):
    mocker.patch(
        "ktp_controller.api.client.get_last_status_report",
        return_value=make_status_report(),
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
    wui_client, override_session, mocker, make_status_report
):
    mocker.patch(
        "ktp_controller.api.client.get_last_status_report",
        return_value=make_status_report(),
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


def test_landing_view_honors_forwarded_prefix(
    wui_client, override_session, mocker, make_status_report
):
    mocker.patch(
        "ktp_controller.api.client.get_last_status_report",
        return_value=make_status_report(),
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
