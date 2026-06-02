# Standard library imports
import asyncio
import datetime
import logging
import time

# Third-party imports


# Internal imports
import ktp_controller.abitti2.client
import ktp_controller.api.client
import ktp_controller.examomatic.client
import ktp_controller.utils

# Relative imports
from .utils import (
    assert_abitti2_running_exams,
    assert_clean_start,
    assert_exam_scheduling_and_download,
    assert_scheduled_exam_package_state_is,
    assert_scheduled_exam_package_gets_started,
    assert_examomatic_shutdown,
)

_LOGGER = logging.getLogger(__name__)

# Test functions are and must be executed sequentially. In unit tests,
# it's not a good idea to build tests which depend on each other, but
# this is integration test scenario, and pytest is just a neat way to
# run them too. So, each test function is a sequential step in the
# testrun.


def test_clean_start(testrunstate):
    testrunstate.student_access_code = assert_clean_start()


def test_first_exam_package_is_scheduled_and_downloaded(utcnow):
    assert_exam_scheduling_and_download(
        exam_title="Integraatiotestikoe1",
        seconds_until_start=60,
        duration_seconds=30,
        lock_time_duration_seconds=30,
        expected_ack_count=1,
        utcnow=utcnow,
    )


def test_first_exam_package_gets_started(testrunstate):
    testrunstate.scheduled_exam_package1 = assert_scheduled_exam_package_gets_started(
        "Integraatiotestikoe1"
    )


def test_first_exam_package_gets_stopped(testrunstate):
    testrunstate.scheduled_exam_package1 = assert_scheduled_exam_package_state_is(
        "stopped", external_id=testrunstate.scheduled_exam_package1["external_id"]
    )


def test_first_exam_package_gets_archived(testrunstate):
    testrunstate.scheduled_exam_package1 = assert_scheduled_exam_package_state_is(
        "archived", external_id=testrunstate.scheduled_exam_package1["external_id"]
    )
    assert asyncio.run(ktp_controller.api.client.get_current_exam_package()) is None


def test_odotusaulakoe_is_running_between_exams():
    assert_abitti2_running_exams(
        lambda running_exams: "Odotusaulakoe" in running_exams, wait=30
    )


def test_examomatic_reboots_constantly_for_30secs_and_agent_restarts(utcnow):
    last_status_report_seen_by_api = asyncio.run(
        ktp_controller.api.client.get_last_status_report()
    )

    ktp_controller_started_at_before_shutdown = datetime.datetime.fromisoformat(
        last_status_report_seen_by_api["ktp_controller"]["started_at"]
    )

    while (ktp_controller.utils.utcnow() - utcnow).total_seconds() <= 30:
        try:
            assert_examomatic_shutdown()
        except Exception:
            pass
        time.sleep(1)

    last_status_report_seen_by_api = asyncio.run(
        ktp_controller.api.client.get_last_status_report()
    )
    ktp_controller_started_at_after_shutdown = datetime.datetime.fromisoformat(
        last_status_report_seen_by_api["ktp_controller"]["started_at"]
    )

    assert (
        ktp_controller_started_at_before_shutdown
        < ktp_controller_started_at_after_shutdown
    )


def test_examomatic_is_running_again():
    for i in range(30):
        try:
            response = asyncio.run(
                ktp_controller.examomatic.client._post("/mock/get_state")
            )
        except Exception as e:
            _LOGGER.warning("Failed to connect: %s", str(e))
        else:
            if response.status_code == 200:
                break
        time.sleep(1)
    assert response.status_code == 200


def test_second_exam_package_is_scheduled_and_downloaded(utcnow):
    assert_exam_scheduling_and_download(
        exam_title="Integraatiotestikoe2",
        seconds_until_start=60,
        duration_seconds=30,
        lock_time_duration_seconds=30,
        expected_ack_count=1,
        utcnow=utcnow,
    )


def test_second_exam_package_gets_started(testrunstate):
    testrunstate.scheduled_exam_package2 = assert_scheduled_exam_package_gets_started(
        "Integraatiotestikoe2"
    )


def test_second_exam_package_gets_stopped(testrunstate):
    testrunstate.scheduled_exam_package2 = assert_scheduled_exam_package_state_is(
        "stopped", external_id=testrunstate.scheduled_exam_package2["external_id"]
    )


def test_second_exam_package_gets_archived(testrunstate):
    testrunstate.scheduled_exam_package2 = assert_scheduled_exam_package_state_is(
        "archived", external_id=testrunstate.scheduled_exam_package2["external_id"]
    )
    assert asyncio.run(ktp_controller.api.client.get_current_exam_package()) is None


def test_odotusaulakoe_is_running_again():
    assert_abitti2_running_exams(
        lambda running_exams: "Odotusaulakoe" in running_exams, wait=30
    )
