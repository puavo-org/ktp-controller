import asyncio

import fastapi.testclient
import pytest

import ktp_controller.api.client
import ktp_controller.wui.auth
import ktp_controller.wui.auth_routes
import ktp_controller.wui.main


@pytest.fixture
def wui_client():
    return fastapi.testclient.TestClient(
        ktp_controller.wui.main.APP, follow_redirects=False
    )


@pytest.fixture(autouse=True)
def _reset_login_rate_limit():
    # TestClient's request.client.host is always "testclient", so
    # every test in this module shares one rate-limit bucket in the
    # real Redis backing it; reset it so tests stay order-independent
    # regardless of hits accumulated by earlier runs/tests.
    asyncio.run(ktp_controller.wui.auth_routes._LOGIN_RATE_LIMITER.reset("testclient"))


def _status_report(username="invigilator1", passphrase="s3cret"):
    return {
        "abitti2": {
            "supervisor_username": username,
            "supervisor_passphrase": passphrase,
        }
    }


def test_get_login_renders_form(wui_client):
    response = wui_client.get("/login")

    assert response.status_code == 200
    assert b"<form" in response.content


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

    logout_response = wui_client.post(
        "/logout",
        cookies={ktp_controller.wui.auth.SESSION_COOKIE_NAME: session_cookie},
        headers=_SAME_ORIGIN_HEADERS,
    )

    assert logout_response.status_code == 303
    assert logout_response.headers["location"] == "/login"
