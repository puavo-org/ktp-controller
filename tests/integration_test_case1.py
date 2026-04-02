# Standard library imports
import asyncio

# Third-party imports


# Internal imports
import ktp_controller.abitti2.client
import ktp_controller.api.client
import ktp_controller.examomatic.client

# Relative imports
from .utils import (
    assert_abitti2_running_exams,
    assert_clean_start,
    assert_exam_scheduling_and_download,
    assert_scheduled_exam_package_state_is,
    assert_scheduled_exam_package_gets_started,
)

# Test functions are and must be executed sequentially. In unit tests,
# it's not a good idea to build tests which depend on each other, but
# this is integration test scenario, and pytest is just a neat way to
# run them too. So, each test function is a sequential step in the
# testrun.


def test_clean_start(testrunstate):
    testrunstate.student_access_code = assert_clean_start()


def test_exam_package_is_scheduled_and_downloaded(utcnow):
    assert_exam_scheduling_and_download(
        exam_title="Integraatiotestikoe1",
        seconds_until_start=60,
        duration_seconds=30,
        lock_time_duration_seconds=30,
        expected_ack_count=1,
        utcnow=utcnow,
    )


def test_exam_package_gets_started(testrunstate):
    testrunstate.scheduled_exam_package1 = assert_scheduled_exam_package_gets_started(
        "Integraatiotestikoe1"
    )


def test_exam_package_gets_stopped_on_time_because_no_students(testrunstate):
    assert_scheduled_exam_package_state_is(
        "stopped", external_id=testrunstate.scheduled_exam_package1["external_id"]
    )


def test_exam_package_gets_archived(testrunstate):
    assert_scheduled_exam_package_state_is(
        "archived", external_id=testrunstate.scheduled_exam_package1["external_id"]
    )
    assert asyncio.run(ktp_controller.api.client.get_current_exam_package()) is None


def test_waiting_lobby_exam_is_running_again():
    assert_abitti2_running_exams(
        lambda running_exams: "Odotusaulakoe" in running_exams, wait=30
    )
