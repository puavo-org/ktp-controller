import asyncio

import pytest

import ktp_controller.api.client
import ktp_controller.wui.auth
import ktp_controller.wui.auth_routes
import ktp_controller.wui.main


@pytest.fixture(autouse=True)
def _reset_login_rate_limit():
    # TestClient's request.client.host is always "testclient", so
    # every test in this module shares one rate-limit bucket in the
    # real Redis backing it; reset it so tests stay order-independent
    # regardless of hits accumulated by earlier runs/tests.
    asyncio.run(ktp_controller.wui.auth_routes._LOGIN_RATE_LIMITER.reset("testclient"))


def _status_report(
    username="invigilator1", passphrase="s3cret", domain="test-server.koe.abitti.net"
):
    return {
        "abitti2": {
            "supervisor_username": username,
            "supervisor_passphrase": passphrase,
            "domain": domain,
        }
    }


def test_get_login_renders_form(wui_client):
    response = wui_client.get("/login")

    assert response.status_code == 200
    assert b"<form" in response.content
    assert b"/logout" not in response.content


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param("/invigilator/", True, id="plain_path"),
        pytest.param("/invigilator/foo", True, id="nested_path"),
        pytest.param("/a", True, id="minimal_path"),
        pytest.param("", False, id="empty"),
        pytest.param("evil.example", False, id="no_leading_slash"),
        pytest.param("https://evil.example/", False, id="absolute_url"),
        pytest.param("//evil.example/", False, id="protocol_relative"),
        pytest.param("/\\evil.example", False, id="leading_backslash"),
        pytest.param("/\t/evil.example", False, id="tab_smuggled_double_slash"),
    ],
)
def test_is_safe_next_path(value, expected):
    assert ktp_controller.wui.auth_routes._is_safe_next_path(value) is expected


def test_get_login_renders_form_with_forwarded_prefix(wui_client):
    # nginx forwards the full, un-stripped path alongside the header (see
    # ktp_controller.nginx.enable_nginx_wui_tls_reverse_proxy).
    response = wui_client.get(
        "/remote/12345/login", headers={"X-Forwarded-Prefix": "/remote/12345"}
    )

    assert response.status_code == 200
    assert b'action="/remote/12345/login"' in response.content
    assert b'value="/remote/12345/invigilator/"' in response.content


@pytest.mark.parametrize(
    "unsafe_next",
    [
        pytest.param("https://evil.example/", id="absolute_url"),
        pytest.param("//evil.example/", id="protocol_relative"),
    ],
)
def test_get_login_falls_back_to_default_next_for_unsafe_value(wui_client, unsafe_next):
    response = wui_client.get("/login", params={"next": unsafe_next})

    assert response.status_code == 200
    assert b'value="/invigilator/"' in response.content
    assert unsafe_next.encode() not in response.content


def test_get_login_preserves_safe_next_value(wui_client):
    response = wui_client.get("/login", params={"next": "/invigilator/foo"})

    assert response.status_code == 200
    assert b'value="/invigilator/foo"' in response.content


def test_get_login_shows_logged_in_state_with_valid_session(wui_client, mocker):
    mocker.patch.object(
        ktp_controller.api.client,
        "get_or_create_user_permissions",
        return_value=["wui.invigilator.view"],
    )
    session_id = asyncio.run(
        ktp_controller.wui.auth.create_session("alice", locale="fi")
    )
    wui_client.cookies = {ktp_controller.wui.auth.SESSION_COOKIE_NAME: session_id}
    try:
        response = wui_client.get(
            "/login",
        )

        assert response.status_code == 200
        assert b"alice" in response.content
        assert b'action="/logout"' in response.content
    finally:
        asyncio.run(ktp_controller.wui.auth.destroy_session(session_id))


# A real browser sends an Origin header on POST form submissions, same-
# origin or not, so a legitimate login/logout request always has one
# matching the app's own host; only the deliberately cross-origin test
# below omits/mismatches it.
_SAME_ORIGIN_HEADERS = {"origin": "http://testserver"}


def test_post_login_wrong_credentials_is_rejected(wui_client, mocker):
    mocker.patch(
        "ktp_controller.api.client.get_last_status_report",
        return_value=_status_report(),
    )

    response = wui_client.post(
        "/login",
        data={"username": "invigilator1", "password": "wrong"},
        headers=_SAME_ORIGIN_HEADERS,
    )

    assert response.status_code == 401
    assert ktp_controller.wui.auth.SESSION_COOKIE_NAME not in response.cookies


def test_post_login_wrong_credentials_does_not_echo_unsafe_next(wui_client, mocker):
    mocker.patch(
        "ktp_controller.api.client.get_last_status_report",
        return_value=_status_report(),
    )

    response = wui_client.post(
        "/login",
        data={
            "username": "invigilator1",
            "password": "wrong",
            "next": "https://evil.example/",
        },
        headers=_SAME_ORIGIN_HEADERS,
    )

    assert response.status_code == 401
    assert b'value="/invigilator/"' in response.content
    assert b"evil.example" not in response.content


def test_post_login_correct_credentials_sets_session_cookie(wui_client, mocker):
    mocker.patch(
        "ktp_controller.api.client.get_last_status_report",
        return_value=_status_report(),
    )
    mocker.patch.object(
        ktp_controller.api.client,
        "get_or_create_user_permissions",
        return_value=["wui.invigilator.view"],
    )

    response = wui_client.post(
        "/login",
        data={"username": "invigilator1", "password": "s3cret"},
        headers=_SAME_ORIGIN_HEADERS,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/invigilator/"
    assert ktp_controller.wui.auth.SESSION_COOKIE_NAME in response.cookies


def test_post_login_correct_credentials_honors_forwarded_prefix(wui_client, mocker):
    mocker.patch(
        "ktp_controller.api.client.get_last_status_report",
        return_value=_status_report(),
    )
    mocker.patch.object(
        ktp_controller.api.client,
        "get_or_create_user_permissions",
        return_value=["wui.invigilator.view"],
    )

    response = wui_client.post(
        "/remote/12345/login",
        data={"username": "invigilator1", "password": "s3cret"},
        headers={**_SAME_ORIGIN_HEADERS, "X-Forwarded-Prefix": "/remote/12345"},
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/remote/12345/invigilator/"


@pytest.mark.parametrize(
    "unsafe_next",
    [
        pytest.param("https://evil.example/", id="absolute_url"),
        pytest.param("//evil.example/", id="protocol_relative"),
        pytest.param("/\\evil.example", id="leading_backslash"),
    ],
)
def test_post_login_falls_back_to_default_next_for_unsafe_value(
    wui_client, mocker, unsafe_next
):
    mocker.patch(
        "ktp_controller.api.client.get_last_status_report",
        return_value=_status_report(),
    )
    mocker.patch.object(
        ktp_controller.api.client,
        "get_or_create_user_permissions",
        return_value=["wui.invigilator.view"],
    )

    response = wui_client.post(
        "/login",
        data={
            "username": "invigilator1",
            "password": "s3cret",
            "next": unsafe_next,
        },
        headers=_SAME_ORIGIN_HEADERS,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/invigilator/"


def test_post_login_preserves_safe_next_value(wui_client, mocker):
    mocker.patch(
        "ktp_controller.api.client.get_last_status_report",
        return_value=_status_report(),
    )
    mocker.patch.object(
        ktp_controller.api.client,
        "get_or_create_user_permissions",
        return_value=["wui.invigilator.view"],
    )

    response = wui_client.post(
        "/login",
        data={
            "username": "invigilator1",
            "password": "s3cret",
            "next": "/invigilator/foo",
        },
        headers=_SAME_ORIGIN_HEADERS,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/invigilator/foo"


def test_post_login_falls_back_to_default_next_honoring_forwarded_prefix(
    wui_client, mocker
):
    mocker.patch(
        "ktp_controller.api.client.get_last_status_report",
        return_value=_status_report(),
    )
    mocker.patch.object(
        ktp_controller.api.client,
        "get_or_create_user_permissions",
        return_value=["wui.invigilator.view"],
    )

    response = wui_client.post(
        "/remote/12345/login",
        data={
            "username": "invigilator1",
            "password": "s3cret",
            "next": "https://evil.example/",
        },
        headers={**_SAME_ORIGIN_HEADERS, "X-Forwarded-Prefix": "/remote/12345"},
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/remote/12345/invigilator/"


def test_post_login_rejects_cross_origin_request(wui_client, mocker):
    mocker.patch(
        "ktp_controller.api.client.get_last_status_report",
        return_value=_status_report(),
    )

    response = wui_client.post(
        "/login",
        data={"username": "invigilator1", "password": "s3cret"},
        headers={"Origin": "https://evil.invalid"},
    )

    assert response.status_code == 403


def test_post_login_is_rate_limited_per_client(wui_client, mocker):
    mocker.patch(
        "ktp_controller.api.client.get_last_status_report",
        return_value=_status_report(),
    )
    mocker.patch.object(
        ktp_controller.wui.auth_routes._LOGIN_RATE_LIMITER,
        "hit",
        return_value=False,
    )

    response = wui_client.post(
        "/login",
        data={"username": "invigilator1", "password": "wrong"},
        headers=_SAME_ORIGIN_HEADERS,
    )

    assert response.status_code == 429


def test_login_page_lang_query_param_overrides_accept_language(wui_client):
    response = wui_client.get("/login?lang=en", headers={"Accept-Language": "fi"})

    assert response.status_code == 200
    assert b'<html lang="en">' in response.content
    assert b"Log in" in response.content


def test_post_locale_persists_choice_in_session(wui_client, mocker):
    mocker.patch(
        "ktp_controller.api.client.get_last_status_report",
        return_value=_status_report(),
    )
    mocker.patch.object(
        ktp_controller.api.client,
        "get_or_create_user_permissions",
        return_value=["wui.invigilator.view"],
    )

    login_response = wui_client.post(
        "/login",
        data={"username": "invigilator1", "password": "s3cret"},
        headers=_SAME_ORIGIN_HEADERS,
    )
    session_cookie = login_response.cookies[ktp_controller.wui.auth.SESSION_COOKIE_NAME]

    wui_client.cookies = {ktp_controller.wui.auth.SESSION_COOKIE_NAME: session_cookie}
    locale_response = wui_client.post(
        "/locale",
        data={"locale": "en", "next": "/login"},
        headers=_SAME_ORIGIN_HEADERS,
    )
    assert locale_response.status_code == 303

    response = wui_client.get("/login")
    assert b'<html lang="en">' in response.content


@pytest.mark.parametrize(
    "unsafe_next",
    [
        pytest.param("https://evil.example/", id="absolute_url"),
        pytest.param("//evil.example/", id="protocol_relative"),
    ],
)
def test_post_locale_falls_back_to_default_next_for_unsafe_value(
    wui_client, unsafe_next
):
    response = wui_client.post(
        "/locale",
        data={"locale": "en", "next": unsafe_next},
        headers=_SAME_ORIGIN_HEADERS,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/invigilator/"


def test_post_locale_preserves_safe_next_value(wui_client):
    response = wui_client.post(
        "/locale",
        data={"locale": "en", "next": "/invigilator/"},
        headers=_SAME_ORIGIN_HEADERS,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/invigilator/"


def test_post_locale_rejects_unsupported_locale(wui_client):
    response = wui_client.post(
        "/locale",
        data={"locale": "de", "next": "/login"},
        headers=_SAME_ORIGIN_HEADERS,
    )

    assert response.status_code == 422


def test_logout_clears_session(wui_client, mocker):
    mocker.patch(
        "ktp_controller.api.client.get_last_status_report",
        return_value=_status_report(),
    )
    mocker.patch.object(
        ktp_controller.api.client,
        "get_or_create_user_permissions",
        return_value=["wui.invigilator.view"],
    )

    login_response = wui_client.post(
        "/login",
        data={"username": "invigilator1", "password": "s3cret"},
        headers=_SAME_ORIGIN_HEADERS,
    )
    session_cookie = login_response.cookies[ktp_controller.wui.auth.SESSION_COOKIE_NAME]

    wui_client.cookies = {ktp_controller.wui.auth.SESSION_COOKIE_NAME: session_cookie}
    logout_response = wui_client.post(
        "/logout",
        headers=_SAME_ORIGIN_HEADERS,
    )

    assert logout_response.status_code == 303
    assert logout_response.headers["location"] == "/login"


def test_logout_honors_forwarded_prefix(wui_client, mocker):
    mocker.patch(
        "ktp_controller.api.client.get_last_status_report",
        return_value=_status_report(),
    )
    mocker.patch.object(
        ktp_controller.api.client,
        "get_or_create_user_permissions",
        return_value=["wui.invigilator.view"],
    )

    login_response = wui_client.post(
        "/login",
        data={"username": "invigilator1", "password": "s3cret"},
        headers=_SAME_ORIGIN_HEADERS,
    )
    session_cookie = login_response.cookies[ktp_controller.wui.auth.SESSION_COOKIE_NAME]

    wui_client.cookies = {ktp_controller.wui.auth.SESSION_COOKIE_NAME: session_cookie}
    logout_response = wui_client.post(
        "/remote/12345/logout",
        headers={**_SAME_ORIGIN_HEADERS, "X-Forwarded-Prefix": "/remote/12345"},
    )

    assert logout_response.status_code == 303
    assert logout_response.headers["location"] == "/remote/12345/login"
