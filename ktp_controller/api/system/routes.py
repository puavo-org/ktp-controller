# Standard library imports
import asyncio
import json
import logging

# Third-party imports
import fastapi
import fastapi.exceptions
import pydantic
import sqlalchemy
import sqlalchemy.orm
import sqlalchemy.sql

import ktp_controller.agent.utils
import ktp_controller.api.utils
import ktp_controller.messages
import ktp_controller.pydantic
import ktp_controller.redis
import ktp_controller.ui
from ktp_controller.api import models

# Internal imports
from ktp_controller.api.database import get_db

# Relative imports
from . import schemas

_LOGGER = logging.getLogger(__name__)


__all__ = [
    "router",
]

router = fastapi.APIRouter(tags=["system"])


async def _keep_silent_websocket_alive(websock: fastapi.WebSocket):
    while True:
        try:
            data = await asyncio.wait_for(websock.receive_json(), timeout=2)
        except fastapi.WebSocketDisconnect:
            _LOGGER.info("Websocket %r disconnected.", websock.client)
            break
        except TimeoutError:
            continue
        except json.decoder.JSONDecodeError:
            _LOGGER.warning(
                "Got invalid json from silent websocket %r!. Disconnecting.",
                websock.client,
            )
            break
        else:
            _LOGGER.warning(
                "Got %r from silent websocket %r! Disconnecting.", data, websock.client
            )
            break


async def _handle_websocket(*asyncfuncs, websock: fastapi.WebSocket, channel: str):
    await websock.accept()
    try:
        await websock.app.state.pubsub_broadcaster.register_websocket(websock, channel)
        async with asyncio.TaskGroup() as tg:
            for asyncfunc in asyncfuncs:
                tg.create_task(asyncfunc(websock))

    finally:
        await websock.app.state.pubsub_broadcaster.unregister_websocket(
            websock, channel
        )


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
    return await ktp_controller.agent.utils.send_command(command_data)


@router.websocket("/ui_websocket")
async def _ui_websocket(websock: fastapi.WebSocket):
    await _handle_websocket(
        _keep_silent_websocket_alive,
        websock=websock,
        channel=ktp_controller.ui.PUBSUB_CHANNEL,
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
    "/send_status_report",
    response_model=None,
    summary="Send status report",
)
async def _send_status_report(
    request: schemas.StatusReport,
    db: sqlalchemy.orm.Session = fastapi.Depends(get_db),
):
    status_report_count = db.query(models.StatusReport).count()
    if status_report_count >= _get_status_report_max_count():
        delete_subquery = (
            db.query(models.StatusReport.dbid)
            .order_by(sqlalchemy.asc(models.StatusReport.dbrow_created_at))
            .limit(status_report_count - _get_status_report_preserve_count())
            .subquery()
        )
        db.query(models.StatusReport).filter(
            models.StatusReport.dbid.in_(sqlalchemy.sql.select(delete_subquery))
        ).delete(synchronize_session="fetch")

    db_status_report = models.StatusReport(
        dbid=None, raw_data=json.loads(request.model_dump_json())
    )
    db.add(db_status_report)
    db.commit()


@router.post(
    "/get_last_status_report",
    response_model=schemas.StatusReport | None,
    summary="Get last status report",
)
async def _get_last_status_report(
    db: sqlalchemy.orm.Session = fastapi.Depends(get_db),
):
    db_status_report = (
        db.query(models.StatusReport)
        .order_by(sqlalchemy.sql.desc(models.StatusReport.dbrow_created_at))
        .limit(1)
        .one_or_none()
    )

    if db_status_report is None:
        return None

    try:
        return schemas.StatusReport.model_validate(db_status_report.raw_data)
    except pydantic.ValidationError:
        # StatusReport table contains temporary volatile data, doing
        # data migrations is not worth it. Hence, we might have
        # "invalid" old data there if the system just restarted after
        # an upgrade. If the latest data is invalid, caller just needs
        # to be more patient, wait couple of seconds, and we should
        # have a fresh valid status report available.
        return None


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
    await _handle_websocket(
        _communicate_with_agent,
        websock=websock,
        channel=ktp_controller.agent.utils.PUBSUB_CHANNEL,
    )


@router.get(
    "/echo",
    response_model=schemas.Echo,
    summary="Get echo response",
)
async def _get_echo(request: fastapi.Request):
    now = ktp_controller.utils.now()

    headers = dict(request.headers)

    return {
        "request": {
            "method": "GET",
            "received_at": now.isoformat(),
            "headers": headers,
        },
    }
