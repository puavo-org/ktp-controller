# Standard library imports
import typing

# Third-party imports
import requests

# Internal imports
import ktp_controller.utils
from ktp_controller.settings import SETTINGS


__all__ = [
    "push_abitti2_status",
]


def _post_json(path, *, data=None, timeout: int = 5) -> requests.Response:
    if data is None:
        data = {}
    return requests.post(
        ktp_controller.utils.get_url(
            f"{SETTINGS.api_host}:{SETTINGS.api_port}", path, use_tls=False
        ),
        json=data,
        timeout=timeout,
    )


def push_abitti2_status(status: typing.Dict, *, timeout: int = 5) -> requests.Response:
    return _post_json(
        "/api/v1/commands/push_abitti2_status", data={"status": status}, timeout=timeout
    )


def sync_exams():
    pass


def change_keycode():
    pass
