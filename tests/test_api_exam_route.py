# Standard library imports
import datetime
import json
import time
import uuid

# Internal imports
from ktp_controller.api import models
import ktp_controller.api.client

# Relative imports
from .data import REAL_ANONYMIZED_EOM_EXAM_INFO_JSON, get_synthetic_exam_info
from .utils import client, testdb, db_engine, utcnow, assert_response

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


def test_get_current_scheduled_exam_package__empty_database(client, testdb, utcnow):
    assert testdb.query(models.ScheduledExamPackage).all() == []

    response = client.post("/api/v1/exam/get_current_scheduled_exam_package")
    assert_response(response, expected_status_code=200)

    assert response.json() == None


def test_get_current_scheduled_exam_package__one_package_and_over_15mins_to_start_time_no_current_yet(
    client, testdb, utcnow
):
    eom_exam_info = get_synthetic_exam_info(
        start_time=utcnow + datetime.timedelta(minutes=15, seconds=1), utcnow=utcnow
    )
    api_exam_info = ktp_controller.api.client.eom_exam_info_to_api_exam_info(
        eom_exam_info
    )

    response = client.post("/api/v1/exam/save_exam_info", json=api_exam_info)
    assert_response(response, expected_status_code=200)

    response = client.post("/api/v1/exam/get_current_scheduled_exam_package")
    assert_response(response, expected_status_code=200)

    assert response.json() == None  # Still None because start_time 30mins in future


def test_get_current_scheduled_exam_package__one_package_and_exactly_15mins_to_start_time_no_current_yet(
    client, testdb, utcnow
):
    eom_exam_info = get_synthetic_exam_info(
        start_time=utcnow + datetime.timedelta(minutes=15),
        utcnow=utcnow,
    )
    api_exam_info = ktp_controller.api.client.eom_exam_info_to_api_exam_info(
        eom_exam_info
    )

    response = client.post("/api/v1/exam/save_exam_info", json=api_exam_info)
    assert_response(response, expected_status_code=200)

    response = client.post("/api/v1/exam/get_current_scheduled_exam_package")
    assert_response(response, expected_status_code=200)

    assert response.json() == api_exam_info["scheduled_exam_packages"][0]


def test_get_current_scheduled_exam_package__one_package_and_under_15mins_to_start_time_no_current_yet(
    client, testdb, utcnow
):
    eom_exam_info = get_synthetic_exam_info(
        start_time=utcnow + datetime.timedelta(minutes=14, seconds=59),
        utcnow=utcnow,
    )
    api_exam_info = ktp_controller.api.client.eom_exam_info_to_api_exam_info(
        eom_exam_info
    )

    response = client.post("/api/v1/exam/save_exam_info", json=api_exam_info)
    assert_response(response, expected_status_code=200)

    response = client.post("/api/v1/exam/get_current_scheduled_exam_package")
    assert_response(response, expected_status_code=200)

    assert response.json() == api_exam_info["scheduled_exam_packages"][0]


def test_get_current_scheduled_exam_package__one_package_and_lock_time_is_far_in_future_but_already_locked_no_current_yet(
    client, testdb, utcnow
):
    eom_exam_info = get_synthetic_exam_info(
        start_time=utcnow + datetime.timedelta(days=3),
        utcnow=utcnow,
    )
    api_exam_info = ktp_controller.api.client.eom_exam_info_to_api_exam_info(
        eom_exam_info
    )
    api_exam_info["scheduled_exam_packages"][0][
        "locked"
    ] = True  # locked is the king, lock_time does not mean anything to us.

    response = client.post("/api/v1/exam/save_exam_info", json=api_exam_info)
    assert_response(response, expected_status_code=200)

    response = client.post("/api/v1/exam/get_current_scheduled_exam_package")
    assert_response(response, expected_status_code=200)

    assert response.json() == api_exam_info["scheduled_exam_packages"][0]


def test_get_current_scheduled_exam_package__one_package_and_it_is_past_start_time_no_current_yet(
    client, testdb, utcnow
):
    eom_exam_info = get_synthetic_exam_info(
        start_time=utcnow - datetime.timedelta(seconds=1),
        utcnow=utcnow,
    )
    api_exam_info = ktp_controller.api.client.eom_exam_info_to_api_exam_info(
        eom_exam_info
    )

    response = client.post("/api/v1/exam/save_exam_info", json=api_exam_info)
    assert_response(response, expected_status_code=200)

    response = client.post("/api/v1/exam/get_current_scheduled_exam_package")
    assert_response(response, expected_status_code=200)

    assert response.json() == api_exam_info["scheduled_exam_packages"][0]


def test_get_current_scheduled_exam_package__one_package_and_it_is_past_end_time_no_current_yet(
    client, testdb, utcnow
):
    eom_exam_info = get_synthetic_exam_info(
        start_time=utcnow - datetime.timedelta(days=1),
        utcnow=utcnow,
    )
    api_exam_info = ktp_controller.api.client.eom_exam_info_to_api_exam_info(
        eom_exam_info
    )

    response = client.post("/api/v1/exam/save_exam_info", json=api_exam_info)
    assert_response(response, expected_status_code=200)

    response = client.post("/api/v1/exam/get_current_scheduled_exam_package")
    assert_response(response, expected_status_code=200)

    assert response.json() == None


def test_get_current_scheduled_exam_package__multiple_locked_packages_starting_at_same_time_no_current_yet(
    client, testdb, utcnow
):
    first_api_exam_info = None
    for i in range(10):
        eom_exam_info = get_synthetic_exam_info(
            start_time=utcnow + datetime.timedelta(minutes=14),
            utcnow=utcnow,
        )
        api_exam_info = ktp_controller.api.client.eom_exam_info_to_api_exam_info(
            eom_exam_info
        )
        if first_api_exam_info is None:
            first_api_exam_info = api_exam_info

        response = client.post("/api/v1/exam/save_exam_info", json=api_exam_info)
        assert_response(response, expected_status_code=200)

    response = client.post("/api/v1/exam/get_current_scheduled_exam_package")
    assert_response(response, expected_status_code=200)

    assert response.json() == first_api_exam_info["scheduled_exam_packages"][0]


def test_get_current_scheduled_exam_package__multiple_locked_packages_last_saved_starting_first_no_current_yet(
    client, testdb, utcnow
):
    for i in range(10):
        eom_exam_info = get_synthetic_exam_info(
            start_time=utcnow + datetime.timedelta(minutes=14 - i),
            utcnow=utcnow,
        )
        api_exam_info = ktp_controller.api.client.eom_exam_info_to_api_exam_info(
            eom_exam_info
        )

        response = client.post("/api/v1/exam/save_exam_info", json=api_exam_info)
        assert_response(response, expected_status_code=200)

    response = client.post("/api/v1/exam/get_current_scheduled_exam_package")
    assert_response(response, expected_status_code=200)

    assert response.json() == api_exam_info["scheduled_exam_packages"][0]


def test_get_current_scheduled_exam_package__multiple_locked_packages_starting_at_same_time_no_current_yet(
    client, testdb, utcnow
):
    first_api_exam_info = None
    for i in range(10):
        eom_exam_info = get_synthetic_exam_info(
            start_time=utcnow + datetime.timedelta(minutes=i),
            utcnow=utcnow,
        )
        api_exam_info = ktp_controller.api.client.eom_exam_info_to_api_exam_info(
            eom_exam_info
        )
        if first_api_exam_info is None:
            first_api_exam_info = api_exam_info

        response = client.post("/api/v1/exam/save_exam_info", json=api_exam_info)
        assert_response(response, expected_status_code=200)

    response = client.post("/api/v1/exam/get_current_scheduled_exam_package")
    assert_response(response, expected_status_code=200)

    assert response.json() == first_api_exam_info["scheduled_exam_packages"][0]


def test_get_current_scheduled_exam_package__save_package_which_starts_sooner_than_the_current(
    client, testdb, utcnow
):
    eom_exam_info1 = get_synthetic_exam_info(
        start_time=utcnow + datetime.timedelta(minutes=15),
        utcnow=utcnow,
    )
    api_exam_info1 = ktp_controller.api.client.eom_exam_info_to_api_exam_info(
        eom_exam_info1
    )

    response = client.post("/api/v1/exam/save_exam_info", json=api_exam_info1)
    assert_response(response, expected_status_code=200)

    response = client.post("/api/v1/exam/get_current_scheduled_exam_package")
    assert_response(response, expected_status_code=200)

    assert response.json() == api_exam_info1["scheduled_exam_packages"][0]

    eom_exam_info2 = get_synthetic_exam_info(
        start_time=utcnow + datetime.timedelta(minutes=1),
        utcnow=utcnow,
    )
    api_exam_info2 = ktp_controller.api.client.eom_exam_info_to_api_exam_info(
        eom_exam_info2
    )

    response = client.post("/api/v1/exam/save_exam_info", json=api_exam_info2)
    assert_response(response, expected_status_code=200)

    response = client.post("/api/v1/exam/get_current_scheduled_exam_package")
    assert_response(response, expected_status_code=200)

    # Still the same first package eventhough the package2 would start
    # sooner. The package which gets selected as current, stays
    # current until it has been archived.
    assert response.json() == api_exam_info1["scheduled_exam_packages"][0]


def test_set_current_scheduled_exam_package_state__empty_database(
    client, testdb, utcnow
):
    response = client.post(
        "/api/v1/exam/set_current_scheduled_exam_package_state",
        json={"external_id": str(uuid.uuid4()), "state": "waiting"},
    )

    assert_response(response, expected_status_code=409)
    assert response.json() == {"detail": "scheduled exam package is not current"}


def test_set_current_scheduled_exam_package_state__empty_database_invalid_input(
    client, testdb, utcnow
):
    response = client.post(
        "/api/v1/exam/set_current_scheduled_exam_package_state",
        json={"external_id": str(uuid.uuid4()), "state": "burp"},
    )

    assert_response(response, expected_status_code=422)
    assert response.json() == {
        "detail": [
            {
                "ctx": {
                    "expected": "'waiting', 'ready', 'running', 'stopping', 'stopped' or "
                    "'archived'"
                },
                "input": "burp",
                "loc": ["body", "state"],
                "msg": "Input should be 'waiting', 'ready', 'running', 'stopping', "
                "'stopped' or 'archived'",
                "type": "enum",
            },
        ]
    }


def test_set_current_scheduled_exam_package_state__set_state_of_exam_package_which_is_not_current(
    client, testdb, utcnow
):
    eom_exam_info = get_synthetic_exam_info(
        start_time=utcnow + datetime.timedelta(minutes=14),
        utcnow=utcnow,
    )
    api_exam_info = ktp_controller.api.client.eom_exam_info_to_api_exam_info(
        eom_exam_info
    )

    response = client.post("/api/v1/exam/save_exam_info", json=api_exam_info)
    assert_response(response, expected_status_code=200)

    response = client.post(
        "/api/v1/exam/set_current_scheduled_exam_package_state",
        json={
            "external_id": api_exam_info["scheduled_exam_packages"][0]["external_id"],
            "state": "waiting",
        },
    )

    assert_response(response, expected_status_code=409)
    assert response.json() == {"detail": "scheduled exam package is not current"}


def test_set_current_scheduled_exam_package_state__set_state_of_current_exam_package_invalid_transition(
    client, testdb, utcnow
):
    eom_exam_info = get_synthetic_exam_info(
        start_time=utcnow + datetime.timedelta(minutes=14),
        utcnow=utcnow,
    )
    api_exam_info = ktp_controller.api.client.eom_exam_info_to_api_exam_info(
        eom_exam_info
    )

    response = client.post("/api/v1/exam/save_exam_info", json=api_exam_info)
    assert_response(response, expected_status_code=200)

    response = client.post("/api/v1/exam/get_current_scheduled_exam_package")
    assert_response(response, expected_status_code=200)

    response = client.post(
        "/api/v1/exam/set_current_scheduled_exam_package_state",
        json={
            "external_id": api_exam_info["scheduled_exam_packages"][0]["external_id"],
            "state": "running",
        },
    )

    assert_response(response, expected_status_code=409)
    assert response.json() == {
        "detail": "state of the current scheduled exam package cannot be changed to running"
    }


def test_set_current_scheduled_exam_package_state__set_state_of_current_exam_package_valid_transitions(
    client, testdb, utcnow
):
    eom_exam_info = get_synthetic_exam_info(
        start_time=utcnow + datetime.timedelta(minutes=14),
        utcnow=utcnow,
    )
    api_exam_info = ktp_controller.api.client.eom_exam_info_to_api_exam_info(
        eom_exam_info
    )

    response = client.post("/api/v1/exam/save_exam_info", json=api_exam_info)
    assert_response(response, expected_status_code=200)

    response = client.post("/api/v1/exam/get_current_scheduled_exam_package")
    assert_response(response, expected_status_code=200)

    assert response.json() == api_exam_info["scheduled_exam_packages"][0]

    assert api_exam_info["scheduled_exam_packages"][0].pop("state") == None
    assert api_exam_info["scheduled_exam_packages"][0].pop("state_changed_at") == None

    for state in ("waiting", "ready", "running", "stopping", "stopped", "archived"):
        utcnow_before_state_change = datetime.datetime.utcnow()
        response = client.post(
            "/api/v1/exam/set_current_scheduled_exam_package_state",
            json={
                "external_id": api_exam_info["scheduled_exam_packages"][0][
                    "external_id"
                ],
                "state": state,
            },
        )
        assert_response(response, expected_status_code=200)

        response = client.post("/api/v1/exam/get_current_scheduled_exam_package")
        assert_response(response, expected_status_code=200)

        current_scheduled_exam_package = response.json()
        assert current_scheduled_exam_package.pop("state") == state
        assert (
            datetime.datetime.fromisoformat(
                current_scheduled_exam_package.pop("state_changed_at")
            )
            > utcnow_before_state_change
        )

        assert (
            current_scheduled_exam_package
            == api_exam_info["scheduled_exam_packages"][0]
        )
