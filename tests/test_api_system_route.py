# Standard library imports
import datetime

# Third-party imports
import fastapi
import pytest

# Internal imports
import ktp_controller.messages
from ktp_controller.api import models

# Relative imports
from .utils import client, testdb, db_engine, utcnow, assert_response

# Each test function executes in a separate session, each session
# starts with an empty database.


@pytest.mark.parametrize("command", ["enable_auto_control", "disable_auto_control"])
def test_async_command_dispatching(
    client: fastapi.testclient.TestClient, testdb, utcnow, command
):
    with client.websocket_connect("/api/v1/system/agent_websocket") as agent_websock:
        response = client.post(
            "/api/v1/system/async_command",
            json={"command": command},
        )
        assert_response(response, expected_status_code=202)
        data = agent_websock.receive_json()
        ktp_controller.messages.CommandMessage.model_validate(data)

        data.pop("uuid")
        assert data == {
            "kind": "command",
            "data": {
                "command": command,
            },
        }


def test_send_status_report__invalid_input(client, testdb, utcnow):
    assert testdb.query(models.StatusReport).all() == []

    response = client.post("/api/v1/system/send_status_report", data={})
    assert_response(response, expected_status_code=422)

    response = client.post("/api/v1/system/send_status_report", json={})
    assert_response(response, expected_status_code=422)

    status_report_with_extra_field = {
        "received_at": ktp_controller.utils.strfdt(utcnow),
        "reported_at": ktp_controller.utils.strfdt(utcnow),
        "status": {},
        "something_extra": True,
        "abitti2": {
            "domain": "funny-server.example.invalid",
            "student_access_code": {
                "key_code": "1234",
                "verification_code": "xx",
            },
            "supervisor_username": "valvoja",
            "supervisor_passphrase": "",
            "version": "",
            "last_message_received_at": ktp_controller.utils.strfdt(utcnow),
            "exams": [],
        },
    }

    response = client.post(
        "/api/v1/system/send_status_report",
        json=status_report_with_extra_field,
    )
    assert_response(response, expected_status_code=422)

    status_report_with_invalid_exams = {
        "received_at": ktp_controller.utils.strfdt(utcnow),
        "reported_at": ktp_controller.utils.strfdt(utcnow),
        "status": {},
        "abitti2": {
            "domain": "funny-server.example.invalid",
            "student_access_code": {
                "key_code": "1234",
                "verification_code": "xx",
            },
            "supervisor_username": "valvoja",
            "supervisor_passphrase": "",
            "version": "",
            "last_message_received_at": ktp_controller.utils.strfdt(utcnow),
            "exams": [1],
        },
    }

    response = client.post(
        "/api/v1/system/send_status_report",
        json=status_report_with_invalid_exams,
    )
    assert_response(response, expected_status_code=422)

    # And after all failed attempts to save invalid input, the database should be still empty.
    assert testdb.query(models.StatusReport).all() == []


def test_send_status_report__valid_minimal_input(client, testdb, utcnow):
    assert testdb.query(models.StatusReport).all() == []

    status_report = {
        "received_at": ktp_controller.utils.strfdt(utcnow),
        "reported_at": ktp_controller.utils.strfdt(utcnow),
        "status": {},
        "abitti2": {
            "domain": None,
            "student_access_code": {
                "key_code": "1234",
                "verification_code": "xx",
            },
            "supervisor_username": "valvoja",
            "supervisor_passphrase": "",
            "version": "",
            "last_message_received_at": ktp_controller.utils.strfdt(utcnow),
            "exams": [],
        },
    }

    response = client.post("/api/v1/system/send_status_report", json=status_report)
    assert_response(response, expected_status_code=200)

    db_status_report = testdb.query(models.StatusReport).one()

    assert (
        db_status_report.dbrow_created_at.replace(tzinfo=datetime.timezone.utc) > utcnow
    )
    assert db_status_report.raw_data == status_report

    response = client.post("/api/v1/system/get_last_status_report")
    assert_response(response, expected_status_code=200)

    assert response.json() == status_report


def test_send_status_report__same_valid_minimal_input_twice(client, testdb, utcnow):
    assert testdb.query(models.StatusReport).all() == []

    status_report = {
        "received_at": ktp_controller.utils.strfdt(utcnow),
        "reported_at": ktp_controller.utils.strfdt(utcnow),
        "status": {},
        "abitti2": {
            "domain": None,
            "student_access_code": {
                "key_code": "1234",
                "verification_code": "xx",
            },
            "supervisor_username": "valvoja",
            "supervisor_passphrase": "",
            "version": "",
            "last_message_received_at": ktp_controller.utils.strfdt(utcnow),
            "exams": [],
        },
    }

    response = client.post("/api/v1/system/send_status_report", json=status_report)
    assert_response(response, expected_status_code=200)

    response = client.post("/api/v1/system/send_status_report", json=status_report)
    assert_response(response, expected_status_code=200)

    db_status_report1, db_status_report2 = (
        testdb.query(models.StatusReport).order_by(models.StatusReport.dbid).all()
    )

    assert (
        db_status_report1.dbrow_created_at.replace(tzinfo=datetime.timezone.utc)
        > utcnow
    )

    assert db_status_report1.dbrow_created_at < db_status_report2.dbrow_created_at

    assert db_status_report1.raw_data == db_status_report2.raw_data == status_report


def test_send_status_report__valid_but_highly_unlikely_status(client, testdb, utcnow):
    assert testdb.query(models.StatusReport).all() == []

    status_report = {
        "received_at": ktp_controller.utils.strfdt(utcnow),
        "reported_at": ktp_controller.utils.strfdt(utcnow),
        "status": {
            "We don't validate the raw status data which comes from Abitti2": True,
            "It can be any kind of dict": [{"valid": True}, 3],
            "We always accept and save it": True,
        },
        "abitti2": {
            "domain": "funny-server.example.invalid",
            "student_access_code": {
                "key_code": "1234",
                "verification_code": "xx",
            },
            "supervisor_username": "valvoja",
            "supervisor_passphrase": "",
            "version": "",
            "last_message_received_at": ktp_controller.utils.strfdt(utcnow),
            "exams": [
                {
                    "uuid": "c7390604-e359-473c-a751-9bd265ad798f",
                    "title": "myexam",
                    "started_at": "2025-03-01T10:00:00.000+0000",
                }
            ],
        },
    }

    response = client.post("/api/v1/system/send_status_report", json=status_report)
    assert_response(response, expected_status_code=200)

    db_status_report = testdb.query(models.StatusReport).one()

    assert (
        db_status_report.dbrow_created_at.replace(tzinfo=datetime.timezone.utc) > utcnow
    )
    assert db_status_report.raw_data == status_report


def test_send_status_report__two_different_reports(client, testdb, utcnow):
    assert testdb.query(models.StatusReport).all() == []

    status_report1 = {
        "received_at": "2025-01-01T10:00:00.000+0000",
        "reported_at": "2025-01-01T10:00:05.000+0000",
        "status": {},
        "abitti2": {
            "domain": "funny-server.example.invalid",
            "student_access_code": {
                "key_code": "1234",
                "verification_code": "xx",
            },
            "supervisor_username": "valvoja",
            "supervisor_passphrase": "first report",
            "version": "1.6.0",
            "last_message_received_at": "2025-01-01T10:00:00.000+0000",
            "exams": [],
        },
    }

    response = client.post("/api/v1/system/send_status_report", json=status_report1)
    assert_response(response, expected_status_code=200)

    status_report2 = {
        "received_at": "2024-01-01T10:00:00.000+0000",  # For the sake of testing, agent's clock goes backward between reports
        "reported_at": "2024-01-01T10:00:05.000+0000",
        "status": {},
        "abitti2": {
            "domain": "funny-server.example.invalid",
            "student_access_code": {
                "key_code": "1234",
                "verification_code": "xx",
            },
            "supervisor_username": "valvoja",
            "supervisor_passphrase": "second report",
            "version": "1.7.0",
            "last_message_received_at": "2025-01-01T10:00:00.000+0000",
            "exams": [],
        },
    }
    response = client.post("/api/v1/system/send_status_report", json=status_report2)
    assert_response(response, expected_status_code=200)

    db_status_report1, db_status_report2 = (
        testdb.query(models.StatusReport).order_by(models.StatusReport.dbid).all()
    )

    assert (
        db_status_report1.dbrow_created_at.replace(tzinfo=datetime.timezone.utc)
        > utcnow
    )

    assert db_status_report1.dbrow_created_at < db_status_report2.dbrow_created_at

    assert db_status_report1.raw_data == status_report1
    assert db_status_report2.raw_data == status_report2
    assert db_status_report1.raw_data != db_status_report2.raw_data

    response = client.post("/api/v1/system/get_last_status_report")
    assert_response(response, expected_status_code=200)

    assert response.json() == status_report2


def test_send_status_report__multiple_reports_exactly_max_count(
    client, testdb, utcnow, mocker
):
    assert testdb.query(models.StatusReport).all() == []

    max_count = 6
    preserve_count = 3

    mocked_get_status_report_max_count = mocker.patch(
        "ktp_controller.api.system.routes._get_status_report_max_count"
    )
    mocked_get_status_report_max_count.return_value = max_count

    mocked_get_status_report_preserve_count = mocker.patch(
        "ktp_controller.api.system.routes._get_status_report_preserve_count"
    )
    mocked_get_status_report_preserve_count.return_value = preserve_count

    status_reports = []
    for i in range(max_count):
        status_report = {
            "received_at": ktp_controller.utils.strfdt(
                utcnow + datetime.timedelta(seconds=i * 5)
            ),
            "reported_at": ktp_controller.utils.strfdt(
                utcnow + datetime.timedelta(seconds=i * 5 + 2)
            ),
            "status": {},
            "abitti2": {
                "domain": "funny-server.example.invalid",
                "student_access_code": {
                    "key_code": "1234",
                    "verification_code": "xx",
                },
                "supervisor_username": "valvoja",
                "supervisor_passphrase": "pass",
                "version": "1.11.0",
                "last_message_received_at": ktp_controller.utils.strfdt(
                    utcnow + datetime.timedelta(seconds=i * 5)
                ),
                "exams": [],
            },
        }

        response = client.post("/api/v1/system/send_status_report", json=status_report)
        assert_response(response, expected_status_code=200)
        status_reports.append(status_report)

    db_status_reports = (
        testdb.query(models.StatusReport).order_by(models.StatusReport.dbid).all()
    )

    assert len(db_status_reports) == max_count

    assert [db_sr.raw_data for db_sr in db_status_reports] == status_reports

    response = client.post("/api/v1/system/get_last_status_report")
    assert_response(response, expected_status_code=200)

    assert response.json() == status_reports[-1]


def test_send_status_report__multiple_reports_less_than_max_count(
    client, testdb, utcnow, mocker
):
    assert testdb.query(models.StatusReport).all() == []

    max_count = 6
    preserve_count = 3
    send_count = 5

    mocked_get_status_report_max_count = mocker.patch(
        "ktp_controller.api.system.routes._get_status_report_max_count"
    )
    mocked_get_status_report_max_count.return_value = max_count

    mocked_get_status_report_preserve_count = mocker.patch(
        "ktp_controller.api.system.routes._get_status_report_preserve_count"
    )
    mocked_get_status_report_preserve_count.return_value = preserve_count

    status_reports = []
    for i in range(send_count):
        status_report = {
            "received_at": ktp_controller.utils.strfdt(
                utcnow + datetime.timedelta(seconds=i * 5)
            ),
            "reported_at": ktp_controller.utils.strfdt(
                utcnow + datetime.timedelta(seconds=i * 5 + 2)
            ),
            "status": {},
            "abitti2": {
                "domain": "funny-server.example.invalid",
                "student_access_code": {
                    "key_code": "1234",
                    "verification_code": "xx",
                },
                "supervisor_username": "valvoja",
                "supervisor_passphrase": "pass",
                "version": "1.11.0",
                "last_message_received_at": ktp_controller.utils.strfdt(
                    utcnow + datetime.timedelta(seconds=i * 5)
                ),
                "exams": [],
            },
        }

        response = client.post("/api/v1/system/send_status_report", json=status_report)
        assert_response(response, expected_status_code=200)
        status_reports.append(status_report)

    db_status_reports = (
        testdb.query(models.StatusReport).order_by(models.StatusReport.dbid).all()
    )

    assert len(db_status_reports) == send_count

    assert [db_sr.raw_data for db_sr in db_status_reports] == status_reports

    response = client.post("/api/v1/system/get_last_status_report")
    assert_response(response, expected_status_code=200)

    assert response.json() == status_reports[-1]


def test_send_status_report__multiple_reports_one_more_than_max_count(
    client, testdb, utcnow, mocker
):
    assert testdb.query(models.StatusReport).all() == []

    max_count = 6
    preserve_count = 3
    send_count = 7

    mocked_get_status_report_max_count = mocker.patch(
        "ktp_controller.api.system.routes._get_status_report_max_count"
    )
    mocked_get_status_report_max_count.return_value = max_count

    mocked_get_status_report_preserve_count = mocker.patch(
        "ktp_controller.api.system.routes._get_status_report_preserve_count"
    )
    mocked_get_status_report_preserve_count.return_value = preserve_count

    status_reports = []
    for i in range(send_count):
        status_report = {
            "received_at": ktp_controller.utils.strfdt(
                utcnow + datetime.timedelta(seconds=i * 5)
            ),
            "reported_at": ktp_controller.utils.strfdt(
                utcnow + datetime.timedelta(seconds=i * 5 + 2)
            ),
            "status": {},
            "abitti2": {
                "domain": "funny-server.example.invalid",
                "student_access_code": {
                    "key_code": "1234",
                    "verification_code": "xx",
                },
                "supervisor_username": "valvoja",
                "supervisor_passphrase": "pass",
                "version": "1.11.0",
                "last_message_received_at": ktp_controller.utils.strfdt(
                    utcnow + datetime.timedelta(seconds=i * 5)
                ),
                "exams": [],
            },
        }

        response = client.post("/api/v1/system/send_status_report", json=status_report)
        assert_response(response, expected_status_code=200)
        status_reports.append(status_report)

    db_status_reports = (
        testdb.query(models.StatusReport).order_by(models.StatusReport.dbid).all()
    )

    assert len(db_status_reports) == preserve_count + 1

    assert [db_sr.raw_data for db_sr in db_status_reports] == status_reports[
        -(preserve_count + 1) :
    ]

    response = client.post("/api/v1/system/get_last_status_report")
    assert_response(response, expected_status_code=200)

    assert response.json() == status_reports[-1]


def test_send_status_report__multiple_reports_many_more_than_max_count(
    client, testdb, utcnow, mocker
):
    assert testdb.query(models.StatusReport).all() == []

    max_count = 6
    preserve_count = 3
    send_count = 23

    mocked_get_status_report_max_count = mocker.patch(
        "ktp_controller.api.system.routes._get_status_report_max_count"
    )
    mocked_get_status_report_max_count.return_value = max_count

    mocked_get_status_report_preserve_count = mocker.patch(
        "ktp_controller.api.system.routes._get_status_report_preserve_count"
    )
    mocked_get_status_report_preserve_count.return_value = preserve_count

    status_reports = []
    for i in range(send_count):
        status_report = {
            "received_at": ktp_controller.utils.strfdt(
                utcnow + datetime.timedelta(seconds=i * 5)
            ),
            "reported_at": ktp_controller.utils.strfdt(
                utcnow + datetime.timedelta(seconds=i * 5 + 2)
            ),
            "status": {},
            "abitti2": {
                "domain": "funny-server.example.invalid",
                "student_access_code": {
                    "key_code": "1234",
                    "verification_code": "xx",
                },
                "supervisor_username": "valvoja",
                "supervisor_passphrase": "pass",
                "version": "1.11.0",
                "last_message_received_at": ktp_controller.utils.strfdt(
                    utcnow + datetime.timedelta(seconds=i * 5)
                ),
                "exams": [],
            },
        }

        response = client.post("/api/v1/system/send_status_report", json=status_report)
        assert_response(response, expected_status_code=200)
        status_reports.append(status_report)

    db_status_reports = (
        testdb.query(models.StatusReport).order_by(models.StatusReport.dbid).all()
    )

    assert len(db_status_reports) == preserve_count + 2

    assert [db_sr.raw_data for db_sr in db_status_reports] == status_reports[
        -(preserve_count + 2) :
    ]

    response = client.post("/api/v1/system/get_last_status_report")
    assert_response(response, expected_status_code=200)

    assert response.json() == status_reports[-1]
