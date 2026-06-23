# Standard library imports
import asyncio
import datetime
import time

# Third-party imports
# Internal imports
import ktp_controller.abitti2.client
import ktp_controller.abitti2.naksu2
import ktp_controller.api.client
import ktp_controller.examomatic.client

# Relative imports
from .utils import (
    assert_abitti2_running_exams,
    assert_all_answer_uploads_are_successful,
    assert_clean_start,
    assert_exam_scheduling_and_download,
    assert_last_status_report_does_not_contain_student_names,
    assert_scheduled_exam_package_gets_started,
    assert_scheduled_exam_package_state_is,
    assert_student_access_code_is_not,
)

# Test functions are and must be executed sequentially. In unit tests,
# it's not a good idea to build tests which depend on each other, but
# this is integration test scenario, and pytest is just a neat way to
# run them too. So, each test function is a sequential step in the
# testrun.


def test_clean_start(testrunstate):
    testrunstate.student_access_code = assert_clean_start()


def test_student1_take_waiting_lobby_exam(student1, testrunstate):
    student1.load()
    student1.start_exam(
        exam_uuid="390e7988-ff0e-42b4-a2e6-d13a969e7103",
        exam_title="Odotusaulakoe",
        access_code=testrunstate.student_access_code,
    )
    student1.end_exam()


def test_student2_take_waiting_lobby_exam_but_do_not_end_it(student2, testrunstate):
    student2.load()
    student2.start_exam(
        exam_uuid="390e7988-ff0e-42b4-a2e6-d13a969e7103",
        exam_title="Odotusaulakoe",
        access_code=testrunstate.student_access_code,
    )


def test_first_exam_package_is_scheduled_and_downloaded(utcnow):
    # Prime examomatic-mock with exam info (single scheduled exam,
    # time intervals are short for testing purposes: 30sec pre-lock
    # time, 30sec lock time, 30 sec run time)
    assert_exam_scheduling_and_download(
        exam_title="Ääkköskoe välilyönneillä integraatiotestaukseen",
        seconds_until_start=60,
        duration_seconds=60,
        lock_time_duration_seconds=30,
        expected_ack_count=1,
        utcnow=utcnow,
    )


def test_first_exam_package_gets_started(testrunstate):
    testrunstate.scheduled_exam_package1 = assert_scheduled_exam_package_gets_started(
        "Ääkköskoe välilyönneillä integraatiotestaukseen"
    )


def test_student_access_code_is_changed_when_exam_package_is_started(
    testrunstate,
):
    testrunstate.student_access_code = assert_student_access_code_is_not(
        testrunstate.student_access_code.key_code,
        testrunstate.student_access_code.verification_code,
    )


def test_student1_take_scheduled_exam(student1, testrunstate):
    student1.relogin()  # Exam has changed, relogin is needed.
    student1.start_exam(
        exam_uuid="53d3594c-cde8-43af-ae00-403ed134eba3",
        exam_title="Ääkköskoe välilyönneillä integraatiotestaukseen",
        access_code=testrunstate.student_access_code,
        expect_exam_instructions=False,  # Already seen in this browsing session, Abitti2 seems to show it only once.
    )
    student1.end_exam()


def test_student2_take_scheduled_exam_but_do_not_end_it(student2, testrunstate):
    student2.relogin()  # Exam has changed, relogin is needed.
    student2.start_exam(
        exam_uuid="53d3594c-cde8-43af-ae00-403ed134eba3",
        exam_title="Ääkköskoe välilyönneillä integraatiotestaukseen",
        access_code=testrunstate.student_access_code,
        expect_exam_instructions=False,  # Already seen in this browsing session, Abitti2 seems to show it only once.
    )


def test_last_status_report_does_not_contain_student_names(student1, student2):
    assert_last_status_report_does_not_contain_student_names(student1, student2)


def test_first_exam_package_does_not_get_stopped_until_second_exam_package_is_locked(
    student2, testrunstate, utcnow
):
    until_scheduled_end = (
        datetime.datetime.fromisoformat(
            testrunstate.scheduled_exam_package1["end_time"]
        )
        - utcnow
    ).total_seconds()
    time.sleep(until_scheduled_end + 10)

    # Still running
    testrunstate.scheduled_exam_package1 = assert_scheduled_exam_package_state_is(
        "running",
        external_id=testrunstate.scheduled_exam_package1["external_id"],
        wait=0,
    )

    # Prime examomatic-mock with exam info (single scheduled exam,
    # time intervals are short for testing purposes: 30sec pre-lock
    # time, 30sec lock time, 30 sec run time)
    assert_exam_scheduling_and_download(
        exam_title="Integraatiotestikoe1",
        seconds_until_start=60,
        duration_seconds=30,
        lock_time_duration_seconds=30,
        expected_ack_count=2,
        utcnow=utcnow,
    )

    # Wait until the first exam package is stopped.
    testrunstate.scheduled_exam_package1 = assert_scheduled_exam_package_state_is(
        "stopped",
        external_id=testrunstate.scheduled_exam_package1["external_id"],
        wait=30,
    )


def test_first_exam_package_gets_archived(testrunstate):
    testrunstate.scheduled_exam_package1 = assert_scheduled_exam_package_state_is(
        "archived",
        external_id=testrunstate.scheduled_exam_package1["external_id"],
        wait=90,
    )


def test_second_exam_package_gets_started(testrunstate):
    testrunstate.scheduled_exam_package2 = assert_scheduled_exam_package_gets_started(
        "Integraatiotestikoe1"
    )


def test_second_exam_package_gets_stopped(testrunstate):
    testrunstate.scheduled_exam_package2 = assert_scheduled_exam_package_state_is(
        "stopped",
        external_id=testrunstate.scheduled_exam_package2["external_id"],
        wait=90,
    )


def test_second_exam_package_gets_archived(testrunstate):
    testrunstate.scheduled_exam_package2 = assert_scheduled_exam_package_state_is(
        "archived",
        external_id=testrunstate.scheduled_exam_package2["external_id"],
        wait=90,
    )
    assert asyncio.run(ktp_controller.api.client.get_current_exam_package()) is None


def test_all_answer_uploads_are_successful():
    assert_all_answer_uploads_are_successful()


def test_odotusaulakoe_is_running_again():
    assert_abitti2_running_exams(
        lambda running_exams: "Odotusaulakoe" in running_exams, wait=30
    )
