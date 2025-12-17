# Standard library imports
import datetime
import json
import time
import uuid

# Internal imports
from ktp_controller.api import models
import ktp_controller.api.client
import ktp_controller.api.exam.schemas
from ktp_controller.examomatic.mock.utils import (
    read_exam_info,
    get_synthetic_exam_info,
)

# Relative imports
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

    eom_exam_info = read_exam_info("REQ1.json")

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

    for i in range(len(eom_exam_info["schedules"])):
        assert (
            ktp_controller.api.exam.schemas.ScheduledExam(
                **api_exam_info["scheduled_exams"][i]
            ).model_dump()
            == client.post(
                "/api/v1/exam/get_scheduled_exam",
                json={"external_id": eom_exam_info["schedules"][i]["id"]},
            ).json()
        )


def test_save_exam_info__real_anonymized_input_start_time_and_end_time_switched_around(
    client, testdb, utcnow
):
    assert testdb.query(models.ExamInfo).all() == []

    eom_exam_info = read_exam_info("REQ1.json")

    api_exam_info = ktp_controller.api.client.eom_exam_info_to_api_exam_info(
        eom_exam_info
    )

    start_time = api_exam_info["scheduled_exam_packages"][0]["start_time"]
    api_exam_info["scheduled_exam_packages"][0]["start_time"] = api_exam_info[
        "scheduled_exam_packages"
    ][0]["end_time"]
    api_exam_info["scheduled_exam_packages"][0]["end_time"] = start_time

    response = client.post("/api/v1/exam/save_exam_info", json=api_exam_info)
    assert_response(response, expected_status_code=422)

    assert response.json() == {
        "detail": [
            {
                "type": "value_error",
                "loc": ["body", "scheduled_exam_packages", 0],
                "msg": "Value error, ('start_time >= end_time', datetime.datetime(2025, 5, 28, 11, 15, tzinfo=TzInfo(0)), datetime.datetime(2025, 5, 28, 5, 0, tzinfo=TzInfo(0)))",
                "input": {
                    "external_id": "49cdca0d-3d77-4fe1-a69b-b89a7ddf46f0",
                    "start_time": "2025-05-28T11:15:00.000+0000",
                    "end_time": "2025-05-28T05:00:00.000+0000",
                    "lock_time": "2025-05-28T04:45:00.000+0000",
                    "locked": True,
                    "scheduled_exam_external_ids": [
                        "5db14454-8d68-47af-9e23-e1bb45170d89",
                        "fe20d1cb-c30d-47f4-88b1-3e7dd492d061",
                    ],
                    "state": None,
                    "state_changed_at": None,
                },
                "ctx": {"error": {}},
            }
        ]
    }


def test_get_current_exam_package__empty_database(client, testdb, utcnow):
    assert testdb.query(models.ScheduledExamPackage).all() == []

    response = client.post("/api/v1/exam/get_current_exam_package")
    assert_response(response, expected_status_code=200)

    assert response.json() == None


def test_get_current_exam_package__one_package_and_over_15mins_to_start_time_no_current_yet(
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

    response = client.post("/api/v1/exam/get_current_exam_package")
    assert_response(response, expected_status_code=200)

    assert response.json() == None  # Still None because start_time 30mins in future


def test_get_current_exam_package__one_package_and_exactly_15mins_to_start_time_no_current_yet(
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

    response = client.post("/api/v1/exam/get_current_exam_package")
    assert_response(response, expected_status_code=200)

    assert response.json() == api_exam_info["scheduled_exam_packages"][0]


def test_get_scheduled_exam_package__non_existing_and_existing_external_ids(
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

    response = client.post(
        "/api/v1/exam/get_scheduled_exam_package", json={"external_id": "foobar"}
    )
    assert_response(response, expected_status_code=200)

    assert response.json() is None

    response = client.post(
        "/api/v1/exam/get_scheduled_exam_package",
        json={
            "external_id": api_exam_info["scheduled_exam_packages"][0]["external_id"]
        },
    )
    assert_response(response, expected_status_code=200)

    assert response.json() == api_exam_info["scheduled_exam_packages"][0]


def test_get_current_exam_package__one_package_and_under_15mins_to_start_time_no_current_yet(
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

    response = client.post("/api/v1/exam/get_current_exam_package")
    assert_response(response, expected_status_code=200)

    assert response.json() == api_exam_info["scheduled_exam_packages"][0]


def test_get_current_exam_package__one_package_and_lock_time_is_far_in_future_but_already_locked_no_current_yet(
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

    response = client.post("/api/v1/exam/get_current_exam_package")
    assert_response(response, expected_status_code=200)

    assert response.json() == api_exam_info["scheduled_exam_packages"][0]


def test_get_current_exam_package__one_package_and_it_is_past_start_time_no_current_yet(
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

    response = client.post("/api/v1/exam/get_current_exam_package")
    assert_response(response, expected_status_code=200)

    assert response.json() == api_exam_info["scheduled_exam_packages"][0]


def test_get_current_exam_package__one_package_and_it_is_past_end_time_no_current_yet(
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

    response = client.post("/api/v1/exam/get_current_exam_package")
    assert_response(response, expected_status_code=200)

    assert response.json() == None


def test_get_current_exam_package__multiple_locked_packages_starting_at_same_time_no_current_yet(
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

    response = client.post("/api/v1/exam/get_current_exam_package")
    assert_response(response, expected_status_code=200)

    assert response.json() == first_api_exam_info["scheduled_exam_packages"][0]


def test_get_current_exam_package__multiple_locked_packages_last_saved_starting_first_no_current_yet(
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

    response = client.post("/api/v1/exam/get_current_exam_package")
    assert_response(response, expected_status_code=200)

    assert response.json() == api_exam_info["scheduled_exam_packages"][0]


def test_get_current_exam_package__multiple_locked_packages_starting_at_same_time_no_current_yet(
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

    response = client.post("/api/v1/exam/get_current_exam_package")
    assert_response(response, expected_status_code=200)

    assert response.json() == first_api_exam_info["scheduled_exam_packages"][0]


def test_get_current_exam_package__save_package_which_starts_sooner_than_the_current(
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

    response = client.post("/api/v1/exam/get_current_exam_package")
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

    response = client.post("/api/v1/exam/get_current_exam_package")
    assert_response(response, expected_status_code=200)

    # Still the same first package eventhough the package2 would start
    # sooner. The package which gets selected as current, stays
    # current until it has been archived.
    assert response.json() == api_exam_info1["scheduled_exam_packages"][0]


def test_set_current_exam_package_state__empty_database(client, testdb, utcnow):
    response = client.post(
        "/api/v1/exam/set_current_exam_package_state",
        json={"external_id": str(uuid.uuid4()), "state": "ready"},
    )

    assert_response(response, expected_status_code=409)
    assert response.json() == {"detail": "scheduled exam package is not current"}


def test_set_current_exam_package_state__empty_database_invalid_input(
    client, testdb, utcnow
):
    response = client.post(
        "/api/v1/exam/set_current_exam_package_state",
        json={"external_id": str(uuid.uuid4()), "state": "burp"},
    )

    assert_response(response, expected_status_code=422)
    assert response.json() == {
        "detail": [
            {
                "ctx": {
                    "expected": "'ready', 'running', 'stopping', 'stopped' or "
                    "'archived'"
                },
                "input": "burp",
                "loc": ["body", "state"],
                "msg": "Input should be 'ready', 'running', 'stopping', "
                "'stopped' or 'archived'",
                "type": "enum",
            },
        ]
    }


def test_set_current_exam_package_state__set_state_of_exam_package_which_is_not_current(
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
        "/api/v1/exam/set_current_exam_package_state",
        json={
            "external_id": api_exam_info["scheduled_exam_packages"][0]["external_id"],
            "state": "ready",
        },
    )

    assert_response(response, expected_status_code=409)
    assert response.json() == {"detail": "scheduled exam package is not current"}


def test_set_current_exam_package_state__set_state_of_current_exam_package_invalid_transition(
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

    response = client.post("/api/v1/exam/get_current_exam_package")
    assert_response(response, expected_status_code=200)

    response = client.post(
        "/api/v1/exam/set_current_exam_package_state",
        json={
            "external_id": api_exam_info["scheduled_exam_packages"][0]["external_id"],
            "state": "running",
        },
    )

    assert_response(response, expected_status_code=409)
    assert response.json() == {
        "detail": "state of the current exam package cannot be changed to running"
    }


def test_set_current_exam_package_state__set_state_of_current_exam_package_valid_transitions(
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

    response = client.post("/api/v1/exam/get_current_exam_package")
    assert_response(response, expected_status_code=200)

    assert response.json() == api_exam_info["scheduled_exam_packages"][0]

    state = api_exam_info["scheduled_exam_packages"][0].pop("state")

    assert state == None
    assert api_exam_info["scheduled_exam_packages"][0].pop("state_changed_at") == None

    for next_state in ("ready", "running", "stopping", "stopped", "archived"):
        utcnow_before_state_change = ktp_controller.utils.utcnow()
        response = client.post(
            "/api/v1/exam/set_current_exam_package_state",
            json={
                "external_id": api_exam_info["scheduled_exam_packages"][0][
                    "external_id"
                ],
                "state": next_state,
            },
        )
        assert_response(response, expected_status_code=200)
        assert response.json() == state
        state = next_state

        get_current_exam_package_response = client.post(
            "/api/v1/exam/get_current_exam_package"
        )
        assert_response(get_current_exam_package_response, expected_status_code=200)

        if next_state == "archived":
            # Exam package is now in the final state, so it is not current anymore
            assert get_current_exam_package_response.json() == None

            assert (
                testdb.query(models.ScheduledExamPackage)
                .filter_by(
                    external_id=api_exam_info["scheduled_exam_packages"][0][
                        "external_id"
                    ]
                )
                .one()
                .state
                == "archived"
            )
        else:
            current_exam_package = get_current_exam_package_response.json()
            state_changed_at = datetime.datetime.fromisoformat(
                current_exam_package.pop("state_changed_at")
            )
            assert current_exam_package.pop("state") == next_state
            assert state_changed_at > utcnow_before_state_change

            assert current_exam_package == api_exam_info["scheduled_exam_packages"][0]

            # "Changing" the state again to the same state does not have any affect.
            response = client.post(
                "/api/v1/exam/set_current_exam_package_state",
                json={
                    "external_id": api_exam_info["scheduled_exam_packages"][0][
                        "external_id"
                    ],
                    "state": next_state,
                },
            )
            assert_response(response, expected_status_code=200)
            assert response.json() == next_state

            get_current_exam_package_response2 = client.post(
                "/api/v1/exam/get_current_exam_package"
            )
            assert_response(
                get_current_exam_package_response2, expected_status_code=200
            )
            assert (
                get_current_exam_package_response.json()
                == get_current_exam_package_response2.json()
            )


def test_set_current_exam_package_state__multiple_locked_packages(
    client, testdb, utcnow
):
    api_exam_infos = []
    for i in range(4):
        eom_exam_info = get_synthetic_exam_info(
            start_time=utcnow + datetime.timedelta(minutes=5 * i),
            duration=datetime.timedelta(10),
            utcnow=utcnow,
        )
        api_exam_info = ktp_controller.api.client.eom_exam_info_to_api_exam_info(
            eom_exam_info
        )

        assert api_exam_info["scheduled_exam_packages"][0]["locked"]

        api_exam_infos.append(api_exam_info)

        response = client.post("/api/v1/exam/save_exam_info", json=api_exam_info)
        assert_response(response, expected_status_code=200)

    for i in range(4):
        response = client.post("/api/v1/exam/get_current_exam_package")
        assert_response(response, expected_status_code=200)

        assert response.json() == api_exam_infos[i]["scheduled_exam_packages"][0]

        state = api_exam_infos[i]["scheduled_exam_packages"][0].pop("state")

        assert state is None

        for next_state in ("ready", "running", "stopping", "stopped", "archived"):
            response = client.post(
                "/api/v1/exam/set_current_exam_package_state",
                json={
                    "external_id": api_exam_infos[i]["scheduled_exam_packages"][0][
                        "external_id"
                    ],
                    "state": next_state,
                },
            )
            assert_response(response, expected_status_code=200)
            assert response.json() == state
            state = next_state
