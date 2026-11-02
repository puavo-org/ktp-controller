# Standard library imports
import asyncio
import datetime

import pytest

import ktp_controller.messages
import ktp_controller.redis

# Third-party imports
# import fastapi
# Internal imports
from ktp_controller.api import models

# Relative imports
from .utils import assert_response

# Each test function executes in a separate session, each session
# starts with an empty database.


# TODO: figure out how to run this. It needs API's pubsub_broadcaster task to be running in the background.
# @pytest.mark.parametrize("command", ["enable_auto_control", "disable_auto_control"])
# def test_async_command_dispatching(
#     client: fastapi.testclient.TestClient, testdb, utcnow, command
# ):
#     with client.websocket_connect("/api/v1/system/agent_websocket") as agent_websock:
#         response = client.post(
#             "/api/v1/system/async_command",
#             json={"command": command},
#         )
#         assert_response(response, expected_status_code=202)
#         data = agent_websock.receive_json()
#         ktp_controller.messages.CommandMessage.model_validate(data)

#         data.pop("uuid")
#         assert data == {
#             "kind": "command",
#             "data": {
#                 "command": command,
#             },
#         }


def test_save_status_report__invalid_input(client, testdb, make_v3_status_report):
    assert testdb.query(models.StatusReport).all() == []

    response = client.post("/api/v1/system/save_status_report", data={})
    assert_response(response, expected_status_code=422)

    response = client.post("/api/v1/system/save_status_report", json={})
    assert_response(response, expected_status_code=422)

    status_report_with_extra_field = make_v3_status_report(is_auto_control_enabled=True)
    status_report_with_extra_field["something_extra"] = True

    response = client.post(
        "/api/v1/system/save_status_report",
        json=status_report_with_extra_field,
    )
    assert_response(response, expected_status_code=422)

    status_report_with_invalid_exams = make_v3_status_report(
        is_auto_control_enabled=True, exams=[1]
    )

    response = client.post(
        "/api/v1/system/save_status_report",
        json=status_report_with_invalid_exams,
    )
    assert_response(response, expected_status_code=422)

    # And after all failed attempts to save invalid input, the database should be still empty.
    assert testdb.query(models.StatusReport).all() == []


def test_save_status_report__valid_minimal_input(
    client, testdb, utcnow, make_v3_status_report
):
    assert testdb.query(models.StatusReport).all() == []

    status_report = make_v3_status_report(
        domain=None, is_auto_control_enabled=True, next_exam_packages=None
    )

    response = client.post("/api/v1/system/save_status_report", json=status_report)
    assert_response(response, expected_status_code=200)

    db_status_report = testdb.query(models.StatusReport).one()

    assert db_status_report.dbrow_created_at.replace(tzinfo=datetime.UTC) > utcnow
    assert db_status_report.raw_data == status_report

    response = client.post("/api/v1/system/get_last_status_report")
    assert_response(response, expected_status_code=200)

    assert response.json() == status_report


def test_save_status_report__same_valid_minimal_input_twice(
    client, testdb, utcnow, make_v3_status_report
):
    assert testdb.query(models.StatusReport).all() == []

    status_report = make_v3_status_report(domain=None, is_auto_control_enabled=True)

    response = client.post("/api/v1/system/save_status_report", json=status_report)
    assert_response(response, expected_status_code=200)

    response = client.post("/api/v1/system/save_status_report", json=status_report)
    assert_response(response, expected_status_code=200)

    db_status_report1, db_status_report2 = (
        testdb.query(models.StatusReport).order_by(models.StatusReport.dbid).all()
    )

    assert db_status_report1.dbrow_created_at.replace(tzinfo=datetime.UTC) > utcnow

    assert db_status_report1.dbrow_created_at < db_status_report2.dbrow_created_at

    assert db_status_report1.raw_data == db_status_report2.raw_data == status_report


def test_save_status_report__valid_but_highly_unlikely_status(
    client, testdb, utcnow, make_v3_status_report
):
    assert testdb.query(models.StatusReport).all() == []

    status_report = make_v3_status_report(
        exams=[
            {
                "uuid": "c7390604-e359-473c-a751-9bd265ad798f",
                "title": "myexam",
                "started_at": "2025-03-01T10:00:00.000+0000",
            }
        ],
    )

    response = client.post("/api/v1/system/save_status_report", json=status_report)
    assert_response(response, expected_status_code=200)

    db_status_report = testdb.query(models.StatusReport).one()

    assert db_status_report.dbrow_created_at.replace(tzinfo=datetime.UTC) > utcnow
    assert db_status_report.raw_data == status_report


def test_save_status_report__two_different_reports(
    client, testdb, utcnow, make_v3_status_report
):
    assert testdb.query(models.StatusReport).all() == []

    status_report1 = make_v3_status_report(
        created_at="2025-01-01T10:00:00.000+0000",
        reported_at="2025-01-01T10:00:05.000+0000",
        supervisor_passphrase="first report",
        abitti2_version="1.6.0",
    )

    response = client.post("/api/v1/system/save_status_report", json=status_report1)
    assert_response(response, expected_status_code=200)

    status_report2 = make_v3_status_report(
        # For the sake of testing, agent's clock goes backward between reports.
        created_at="2024-01-01T10:00:00.000+0000",
        reported_at="2024-01-01T10:00:05.000+0000",
        last_message_received_at="2025-01-01T10:00:00.000+0000",
        supervisor_passphrase="second report",
        abitti2_version="1.7.0",
        current_exam_package={
            "uuid": "eff706bd-245b-4f45-ae2a-1e7ae760142e",
            "scheduled_start_time": "1970-01-01T02:00:00.000+0000",
            "scheduled_end_time": "2970-01-01T01:01:01.010+0000",
            "scheduled_lock_time": "1970-01-01T01:01:01.010+0000",
            "state": "running",
            "state_changed_at": "1970-01-01T02:01:01.010+0000",
            "started_at": "1970-01-01T02:01:01.010+0000",
            "archived_at": None,
        },
    )
    response = client.post("/api/v1/system/save_status_report", json=status_report2)
    assert_response(response, expected_status_code=200)

    db_status_report1, db_status_report2 = (
        testdb.query(models.StatusReport).order_by(models.StatusReport.dbid).all()
    )

    assert db_status_report1.dbrow_created_at.replace(tzinfo=datetime.UTC) > utcnow

    assert db_status_report1.dbrow_created_at < db_status_report2.dbrow_created_at

    assert db_status_report1.raw_data == status_report1
    assert db_status_report2.raw_data == status_report2
    assert db_status_report1.raw_data != db_status_report2.raw_data

    response = client.post("/api/v1/system/get_last_status_report")
    assert_response(response, expected_status_code=200)

    assert response.json() == status_report2


def _build_status_reports(make_v3_status_report, utcnow, count, *, cached_files=None):
    return [
        make_v3_status_report(
            created_at=utcnow + datetime.timedelta(seconds=i * 5),
            reported_at=utcnow + datetime.timedelta(seconds=i * 5 + 2),
            supervisor_passphrase="pass",
            abitti2_version="1.11.0",
            cached_files=cached_files,
        )
        for i in range(count)
    ]


@pytest.mark.parametrize(
    ("send_count", "expected_kept_count", "cached_files"),
    [
        pytest.param(6, 6, None, id="exactly_max_count"),
        pytest.param(5, 5, None, id="less_than_max_count"),
        pytest.param(7, 4, None, id="one_more_than_max_count"),
        # Overflowing by a lot keeps one extra report beyond preserve_count
        # (apparently a side effect of how the cleanup trims in batches).
        pytest.param(
            23,
            5,
            {"exams": [], "exam_packages": [], "answers": []},
            id="many_more_than_max_count",
        ),
    ],
)
def test_save_status_report__multiple_reports(
    client,
    testdb,
    utcnow,
    mocker,
    make_v3_status_report,
    send_count,
    expected_kept_count,
    cached_files,
):
    assert testdb.query(models.StatusReport).all() == []

    preserve_count = 3
    mocker.patch(
        "ktp_controller.api.system.routes._get_status_report_max_count",
        return_value=6,
    )
    mocker.patch(
        "ktp_controller.api.system.routes._get_status_report_preserve_count",
        return_value=preserve_count,
    )

    status_reports = _build_status_reports(
        make_v3_status_report, utcnow, send_count, cached_files=cached_files
    )
    for status_report in status_reports:
        response = client.post("/api/v1/system/save_status_report", json=status_report)
        assert_response(response, expected_status_code=200)

    db_status_reports = (
        testdb.query(models.StatusReport).order_by(models.StatusReport.dbid).all()
    )

    assert len(db_status_reports) == expected_kept_count
    assert [db_sr.raw_data for db_sr in db_status_reports] == status_reports[
        -expected_kept_count:
    ]

    response = client.post("/api/v1/system/get_last_status_report")
    assert_response(response, expected_status_code=200)

    assert response.json() == status_reports[-1]


def test_save_raw_abitti2_stats_message(client, testdb, mocker):
    broadcast_mock = mocker.patch(
        "ktp_controller.ui.broadcast_abitti2_stats_changed",
        new=mocker.AsyncMock(return_value="some-uuid"),
    )

    message = {"some": "raw-abitti2-stats-payload"}

    response = client.post(
        "/api/v1/system/save_raw_abitti2_stats_message", json=message
    )
    assert_response(response, expected_status_code=200)

    stored = asyncio.run(ktp_controller.redis.RAW_ABITTI2_STATS_MESSAGES.getall())
    assert stored[0] == message

    broadcast_mock.assert_awaited_once_with()
