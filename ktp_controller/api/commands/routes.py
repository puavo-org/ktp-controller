# Standard library imports
import logging

# Third-party imports
import fastapi  # type: ignore

# import sqlalchemy.orm

# Internal imports
import ktp_controller.abitti2.client
import ktp_controller.abitti2.naksu2
import ktp_controller.examomatic.client

# from ktp_controller.api.database import get_db
from . import schemas


_LOGGER = logging.getLogger(__name__)


__all__ = [
    "router",
]

router = fastapi.APIRouter(tags=["commands"])


@router.post(
    "/push_abitti2_status",
    response_model=schemas.PushAbitti2StatusResponse,
    summary="Push Abitti2 status",
)
def _push_abitti2_status(
    request: schemas.PushAbitti2StatusRequest,
    #    db: sqlalchemy.orm.Session = fastapi.Depends(get_db),
):
    """
    Update status
    """
    # TODO: error handling

    # Before sending Abitti2 status to Exam-o-Matic, we need to add a
    # bit more information.

    examomatic_message = {
        "monitoring_passphrase": ktp_controller.abitti2.naksu2.read_password(),
        "server_version": ktp_controller.abitti2.client.get_version(),
        "status": request.status,
    }

    try:
        single_security_code = ktp_controller.abitti2.client.get_single_security_code()[
            "securityCode"
        ]
    except KeyError:
        # TODO: It's not always there, why not?
        pass
    else:
        examomatic_message["status"]["singleSecurityCode"] = single_security_code

    examomatic_response = ktp_controller.examomatic.client.push_abitti2_status(
        examomatic_message
    )

    return {"ok": examomatic_response.ok}
