import typing

import requests
import requests.auth

import ktp_controller.utils
import ktp_controller.abitti2.naksu2

_ABITTI2_USERNAME = "valvoja"


def get_json(path: str, *, timeout: int = 20) -> typing.Any:
    host = ktp_controller.abitti2.naksu2.read_domain()
    url = ktp_controller.utils.get_url(host, path)

    response = requests.get(
        url,
        auth=requests.auth.HTTPBasicAuth(
            _ABITTI2_USERNAME, ktp_controller.abitti2.naksu2.read_password()
        ),
        timeout=timeout,
    )

    response.raise_for_status()

    return response.json()


def get_version() -> str:
    return get_json("/api/version")["version"]


def get_single_security_code() -> typing.Dict:
    return get_json("/api/single-security-code")


def open_websock():
    password = ktp_controller.abitti2.naksu2.read_password()
    host = ktp_controller.abitti2.naksu2.read_domain()

    return ktp_controller.utils.open_websock(
        host,
        "/ws/stats",
        header={
            "Authorization": ktp_controller.utils.get_basic_auth(
                _ABITTI2_USERNAME, password
            )
        },
    )
