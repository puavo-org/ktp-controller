# Standard library imports
import asyncio
import json
import logging

# Third-party imports
import fastapi  # type: ignore
import fastapi.exceptions  # type: ignore
import pydantic
import sqlalchemy
import sqlalchemy.orm
import sqlalchemy.sql

# Internal imports
from ktp_controller.api.database import get_db
from ktp_controller.api import models

import ktp_controller.agent
import ktp_controller.messages
import ktp_controller.redis
import ktp_controller.pydantic
import ktp_controller.api.utils
import ktp_controller.ui

# Relative imports
from . import schemas

_LOGGER = logging.getLogger(__name__)


__all__ = [
    "router",
]

router = fastapi.APIRouter(tags=["system"])


@router.post(
    "/async_command",
    response_model=pydantic.UUID4,
    status_code=202,
    summary="""\
Asynchronously execute command.
Command will be executed soon after the response is sent.
Return asynchronous message UUID as application/json body.
""",
)
async def _async_command(command_data: ktp_controller.messages.CommandData):
    return await ktp_controller.agent.send_command(command_data)


@router.websocket("/ui_websocket")
async def _ui_websocket(websock: fastapi.WebSocket):
    await websock.accept()

    async with ktp_controller.redis.pubsub(ktp_controller.ui.PUBSUB_CHANNEL) as pubsub:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(
                ktp_controller.api.utils.deliver_pubsub_messages_to_websock(
                    pubsub, websock
                )
            )


# How many status reports will ever get stored at most. If this limit
# is hit, then latest _get_status_report_preserve_count() will be
# preserved and all the rest deleted.
# approx. 60 / 5 * 60 * 24 * 2
# which means 2 days of reports will be stored, Abitti2 sends one report every 5secs
# This constant is implemented as a function so that it can be easily mocked in tests.
def _get_status_report_max_count():
    return 35000


def _get_status_report_preserve_count():
    # 360 difference, means that delete will hit twice per hour
    # because Abitti2 sends status reports one per 5sec.
    return _get_status_report_max_count() - 360  # 60 / 5 * 30 = 360


# Logical invariant
assert 0 < _get_status_report_preserve_count() < _get_status_report_max_count()


@router.post(
    "/send_abitti2_status_report",
    response_model=None,
    summary="Send status report",
)
async def _send_abitti2_status_report(
    request: schemas.Abitti2StatusReport,
    db: sqlalchemy.orm.Session = fastapi.Depends(get_db),
):
    status_report_count = db.query(models.Abitti2StatusReport).count()
    if status_report_count >= _get_status_report_max_count():
        delete_subquery = (
            db.query(models.Abitti2StatusReport.dbid)
            .order_by(sqlalchemy.asc(models.Abitti2StatusReport.dbrow_created_at))
            .limit(status_report_count - _get_status_report_preserve_count())
            .subquery()
        )
        db.query(models.Abitti2StatusReport).filter(
            models.Abitti2StatusReport.dbid.in_(sqlalchemy.sql.select(delete_subquery))
        ).delete(synchronize_session="fetch")

    db_status_report = models.Abitti2StatusReport(
        dbid=None, raw_data=json.loads(request.model_dump_json())
    )
    db.add(db_status_report)
    db.commit()


@router.post(
    "/get_last_abitti2_status_report",
    response_model=schemas.Abitti2StatusReport | None,
    summary="Get last Abitti2 status report",
)
async def _get_last_abitti2_status_report(
    db: sqlalchemy.orm.Session = fastapi.Depends(get_db),
):
    db_status_report = (
        db.query(models.Abitti2StatusReport)
        .order_by(sqlalchemy.sql.desc(models.Abitti2StatusReport.dbrow_created_at))
        .limit(1)
        .one_or_none()
    )

    return None if db_status_report is None else db_status_report.raw_data


async def _communicate_with_agent(websock: fastapi.WebSocket):
    async for message in websock.iter_json():
        if message["kind"] == ktp_controller.messages.MessageKind.PING:
            ping_message = ktp_controller.messages.PingMessage.model_validate(message)
            pong_message = ktp_controller.messages.PongMessage(
                data=ktp_controller.messages.PongData(ping_uuid=ping_message.uuid)
            )
            await websock.send_json(
                ktp_controller.pydantic.json_serializable(pong_message)
            )
            continue
        if message["kind"] == ktp_controller.messages.MessageKind.COMMAND_RESULT:
            command_result_message = (
                ktp_controller.messages.CommandResultMessage.model_validate(message)
            )
            if command_result_message.data.command_status.startswith("error_"):
                _LOGGER.error(
                    "Agent command %r failed", command_result_message.data.command_uuid
                )
            await ktp_controller.ui.forward_command_result_message(
                command_result_message
            )
            _LOGGER.info("forwarded command result successfully")
            continue
        if message["kind"] == ktp_controller.messages.MessageKind.STATUS_REPORT:
            status_report_message = (
                ktp_controller.messages.StatusReportMessage.model_validate(message)
            )
            await ktp_controller.ui.forward_status_report_message(status_report_message)
            _LOGGER.info("forwarded status report successfully")
            continue
        _LOGGER.warning("Received and ignored unknown message: %s", message)


@router.websocket("/agent_websocket")
async def _agent_websocket(
    websock: fastapi.WebSocket,
):
    await websock.accept()

    async with ktp_controller.redis.pubsub(
        ktp_controller.agent.PUBSUB_CHANNEL
    ) as pubsub:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(
                ktp_controller.api.utils.deliver_pubsub_messages_to_websock(
                    pubsub, websock
                )
            )
            tg.create_task(_communicate_with_agent(websock))
