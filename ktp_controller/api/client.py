# Standard library imports
import typing

# Third-party imports
import requests

# Internal imports
import ktp_controller.utils
from ktp_controller.settings import SETTINGS


def post_json(path, data, *, timeout: int = 5) -> requests.Response:
    return requests.post(
        ktp_controller.utils.get_url(
            f"{SETTINGS.api_host}:{SETTINGS.api_port}", path, use_tls=False
        ),
        json={"data": data},
        timeout=timeout,
    )


def post_api_v1_abitti2_status(
    message: typing.Dict, *, timeout: int = 5
) -> requests.Response:
    return post_json("/api/v1/abitti2/status", message, timeout=timeout)


def sync_exams():
    pass


def change_keycode():
    pass
