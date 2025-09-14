# Standard library imports
import logging

# Third-party imports
import fastapi  # type: ignore

# import sqlalchemy.orm

# Internal imports
import ktp_controller.abitti2.client
import ktp_controller.examomatic.client

# from ktp_controller.api.database import get_db
from . import schemas


_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.INFO)


__all__ = [
    "router",
]

router = fastapi.APIRouter(tags=["status"])


@router.post(
    "/update_abitti2_status",
    response_model=schemas.UpdateAbitti2StatusResponse,
    summary="Update Abitti2 status",
)
def _update_abitti2_status(
    request: schemas.UpdateAbitti2StatusRequest,
    #    db: sqlalchemy.orm.Session = fastapi.Depends(get_db),
):
    """
    Update Abitti2 status
    """
    # TODO: error handling

    # Before sending Abitti2 status to Exam-o-Matic, we need to add a
    # bit more information.

    examomatic_message = {
        "monitoring_passphrase": ktp_controller.abitti2.utils.read_password(),
        "server_version": ktp_controller.abitti2.client.get_version(),
        "status": request.data,
    }

    examomatic_message["status"][
        "singleSecurityCode"
    ] = ktp_controller.abitti2.client.get_single_security_code()["securityCode"]

    examomatic_response = (
        ktp_controller.examomatic.client.post_v1_servers_status_update(
            examomatic_message
        )
    )

    return {"ok": examomatic_response.ok}
