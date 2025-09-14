import typing

import requests
import requests.auth

import ktp_controller.utils
import ktp_controller.abitti2.utils


def get_json(path: str, *, timeout: int = 20) -> typing.Any:
    host = ktp_controller.abitti2.utils.read_domain()
    url = ktp_controller.utils.get_url(host, path)

    response = requests.get(
        url,
        auth=requests.auth.HTTPBasicAuth(
            "valvoja", ktp_controller.abitti2.utils.read_password()
        ),
        timeout=timeout,
    )

    response.raise_for_status()

    return response.json()


def get_version() -> str:
    return get_json("/api/version")["version"]


def get_single_security_code() -> typing.Dict:
    return get_json("/api/single-security-code")
