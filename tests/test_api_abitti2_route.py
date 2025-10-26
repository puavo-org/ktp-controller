import datetime
import json

import pytest
import fastapi

# Internal imports
# from .data import REAL_ANONYMIZED_ABITTI2_STATUS_REPORT_JSON
from .utils import client, testdb, db_engine, utcnow, assert_response
from ktp_controller.api import models
import ktp_controller.api.abitti2.schemas as abitti2_schemas
import ktp_controller.api.client

# Each test function executes in a separate session, each session
# starts with an empty database.


def test_send_abitti2_status_report__invalid_input(client, testdb, utcnow):
    assert testdb.query(models.Abitti2StatusReport).all() == []

    response = client.post("/api/v1/abitti2/send_abitti2_status_report", data={})
    assert_response(response, expected_status_code=422)

    response = client.post("/api/v1/abitti2/send_abitti2_status_report", json={})
    assert_response(response, expected_status_code=422)

    status_report_with_extra_field = {
        "received_at": utcnow.isoformat(),
        "reported_at": utcnow.isoformat(),
        "monitoring_passphrase": "",
        "server_version": "",
        "status": {},
        "something_extra": True,
    }

    response = client.post(
        "/api/v1/abitti2/send_abitti2_status_report",
        json=status_report_with_extra_field,
    )
    assert_response(response, expected_status_code=422)

    # And after all failed attempts to save invalid input, the database should be still empty.
    assert testdb.query(models.Abitti2StatusReport).all() == []


def test_send_abitti2_status_report__valid_minimal_input(client, testdb, utcnow):
    assert testdb.query(models.Abitti2StatusReport).all() == []

    status_report = {
        "received_at": utcnow.isoformat(),
        "reported_at": utcnow.isoformat(),
        "monitoring_passphrase": "",
        "server_version": "",
        "status": {},
    }

    response = client.post(
        "/api/v1/abitti2/send_abitti2_status_report", json=status_report
    )
    assert_response(response, expected_status_code=200)

    db_abitti2_status_report = testdb.query(models.Abitti2StatusReport).one()

    assert db_abitti2_status_report.dbrow_created_at > utcnow
    assert db_abitti2_status_report.raw_data == status_report


def test_send_abitti2_status_report__same_valid_minimal_input_twice(
    client, testdb, utcnow
):
    assert testdb.query(models.Abitti2StatusReport).all() == []

    status_report = {
        "received_at": utcnow.isoformat(),
        "reported_at": utcnow.isoformat(),
        "monitoring_passphrase": "",
        "server_version": "",
        "status": {},
    }

    response = client.post(
        "/api/v1/abitti2/send_abitti2_status_report", json=status_report
    )
    assert_response(response, expected_status_code=200)

    response = client.post(
        "/api/v1/abitti2/send_abitti2_status_report", json=status_report
    )
    assert_response(response, expected_status_code=200)

    db_abitti2_status_report1, db_abitti2_status_report2 = (
        testdb.query(models.Abitti2StatusReport)
        .order_by(models.Abitti2StatusReport.dbid)
        .all()
    )

    assert db_abitti2_status_report1.dbrow_created_at > utcnow

    assert (
        db_abitti2_status_report1.dbrow_created_at
        < db_abitti2_status_report2.dbrow_created_at
    )

    assert (
        db_abitti2_status_report1.raw_data
        == db_abitti2_status_report2.raw_data
        == status_report
    )


def test_send_abitti2_status_report__valid_but_highly_unlikely_abitti2_status(
    client, testdb, utcnow
):
    assert testdb.query(models.Abitti2StatusReport).all() == []

    status_report = {
        "received_at": utcnow.isoformat(),
        "reported_at": utcnow.isoformat(),
        "monitoring_passphrase": "",
        "server_version": "",
        "status": {
            "We don't validate the raw status data which comes from Abitti2": True,
            "It can be any kind of dict": [{"valid": True}, 3],
            "We always accept and save it": True,
        },
    }

    response = client.post(
        "/api/v1/abitti2/send_abitti2_status_report", json=status_report
    )
    assert_response(response, expected_status_code=200)

    db_abitti2_status_report = testdb.query(models.Abitti2StatusReport).one()

    assert db_abitti2_status_report.dbrow_created_at > utcnow
    assert db_abitti2_status_report.raw_data == status_report
