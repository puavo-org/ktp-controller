import datetime
import json

import pytest
import fastapi

# Internal imports
from .data import REAL_ANONYMIZED_EOM_EXAM_INFO_JSON
from .utils import client, testdb, db_engine, utcnow, assert_response
from ktp_controller.api import models
import ktp_controller.api.exam.schemas as exam_schemas
import ktp_controller.api.exam.utils as exam_utils
import ktp_controller.api.client

# Each test function executes in a separate session, each session
# starts with an empty database.


def test_save_exam_info__invalid_input(client, testdb, utcnow):
    assert testdb.query(models.ExamInfo).all() == []

    response = client.post("/api/v1/exam/save_exam_info", data={})
    assert_response(response, expected_status_code=422)

    response = client.post("/api/v1/exam/save_exam_info", json={})
    assert_response(response, expected_status_code=422)

    response = client.post(
        "/api/v1/exam/save_exam_info",
        json={
            "scheduled_exams": [],
            "scheduled_exam_packages": [],
            "request_id": 123,  # invalid request_id
            "raw_data": {},
        },
    )
    assert_response(response, expected_status_code=422)

    response = client.post(
        "/api/v1/exam/save_exam_info",
        json={
            "scheduled_exams": [],
            "scheduled_exam_packages": [],
            "request_id": "req123",
            "raw_data": [],  # invalid raw_data, must be dict
            "extrafield": 3,
        },
    )
    assert_response(response, expected_status_code=422)

    response = client.post(
        "/api/v1/exam/save_exam_info",
        json={
            "scheduled_exams": [],
            "scheduled_exam_packages": [],
            "request_id": "req123",
            "raw_data": {},
            "nonexistingbadfield": 3,  # fields not in the schema must not be accepted
        },
    )
    assert_response(response, expected_status_code=422)

    # There are unlimited number of ways the input could be invalid;
    # the point of these assertions is to ensure the input is
    # validated somehow. And because we use Pydantic, the input is
    # validated against schema models.

    # And after all failed attempts to save invalid input, the database should be still empty.
    assert testdb.query(models.ExamInfo).all() == []


def test_save_exam_info__valid_minimal_input(client, testdb, utcnow):
    assert testdb.query(models.ExamInfo).all() == []

    api_exam_info = {
        "scheduled_exams": [],
        "scheduled_exam_packages": [],
        "request_id": "some_kind_of_request_id1",
        # raw_data does not have any functional value, it is just
        # stored to DB as is for debugging and error tracking
        # purposes. So, we just leave this empty in these tests. In
        # real world, the original raw data received from Exam-O-Matic is
        # stored here.
        "raw_data": {},
    }

    response = client.post("/api/v1/exam/save_exam_info", json=api_exam_info)
    assert_response(response, expected_status_code=200)

    assert response.json() == None  # save_exam_info does not return anything currently

    db_exam_info = testdb.query(models.ExamInfo).one()

    assert db_exam_info.raw_data == api_exam_info["raw_data"]
    assert db_exam_info.request_id == api_exam_info["request_id"]


def test_save_exam_info__valid_minimal_input_but_save_twice(client, testdb, utcnow):
    assert testdb.query(models.ExamInfo).count() == 0

    api_exam_info = {
        "scheduled_exams": [],
        "scheduled_exam_packages": [],
        "request_id": "some_kind_of_request_id1",
        "raw_data": {},
    }

    response1 = client.post("/api/v1/exam/save_exam_info", json=api_exam_info)
    assert_response(response1, expected_status_code=200)

    assert testdb.query(models.ExamInfo).count() == 1

    response2 = client.post("/api/v1/exam/save_exam_info", json=api_exam_info)
    assert_response(response2, expected_status_code=409)

    assert testdb.query(models.ExamInfo).count() == 1


def test_save_exam_info__valid_minimal_input_but_save_twice_but_with_different_request_ids(
    client, testdb, utcnow
):
    assert testdb.query(models.ExamInfo).all() == []

    api_exam_info = {
        "scheduled_exams": [],
        "scheduled_exam_packages": [],
        "request_id": "some_kind_of_request_id1",
        "raw_data": {},
    }

    response1 = client.post("/api/v1/exam/save_exam_info", json=api_exam_info)
    assert_response(response1, expected_status_code=200)

    assert testdb.query(models.ExamInfo).count() == 1

    api_exam_info["request_id"] = "different_id"
    response2 = client.post("/api/v1/exam/save_exam_info", json=api_exam_info)
    assert_response(response2, expected_status_code=200)

    assert testdb.query(models.ExamInfo).count() == 2


def test_save_exam_info__real_anonymized_input(client, testdb, utcnow):
    assert testdb.query(models.ExamInfo).all() == []

    eom_exam_info = json.loads(REAL_ANONYMIZED_EOM_EXAM_INFO_JSON)

    api_exam_info = ktp_controller.api.client.eom_exam_info_to_api_exam_info(
        eom_exam_info
    )

    response = client.post("/api/v1/exam/save_exam_info", json=api_exam_info)
    assert_response(response, expected_status_code=200)

    assert response.json() == None

    db_exam_info = testdb.query(models.ExamInfo).one()

    assert db_exam_info.raw_data == api_exam_info["raw_data"] == eom_exam_info
    assert (
        db_exam_info.request_id
        == api_exam_info["request_id"]
        == eom_exam_info["request_id"]
    )
