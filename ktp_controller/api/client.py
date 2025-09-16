# Standard library imports
import json
import typing

# Third-party imports
import requests

# Internal imports
import ktp_controller.utils


def post_json(path, data, *, timeout: int = 5) -> requests.Response:
    return requests.post(
        ktp_controller.utils.get_url("127.0.0.1:8000", path, use_tls=False),
        json={"data": data},
        timeout=timeout,
    )


def update_abitti2_status(
    message: typing.Dict, *, timeout: int = 5
) -> requests.Response:
    return post_json("/api/v1/status/update_abitti2_status", message)


def sync_exams():
    pass


def change_keycode():
    pass
