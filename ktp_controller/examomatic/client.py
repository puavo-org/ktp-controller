# Standard library imports
import json
import typing

# Third-party imports
import requests
import requests.auth

# Internal imports
import ktp_controller.utils
from ktp_controller.settings import SETTINGS


def post_v1_servers_status_update(
    data: typing.Dict, *, timeout: int = 20
) -> requests.Response:
    return requests.post(
        ktp_controller.utils.get_url(
            SETTINGS.examomatic_host, "/v1/servers/status_update"
        ),
        data=json.dumps(data),
        auth=requests.auth.HTTPBasicAuth(
            SETTINGS.examomatic_username,
            ktp_controller.utils.readfirstline(
                SETTINGS.examomatic_password_file, encoding="ascii"
            ),
        ),
        params={
            "domain": SETTINGS.domain,
            "hostname": SETTINGS.hostname,
            "id": SETTINGS.id,
        },
        timeout=timeout,
    )
