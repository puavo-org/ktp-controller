# Standard library imports
import datetime
import dataclasses
import enum
import json
import random
import re
import sys
import time

from typing import Callable

# Third-party imports

# Internal imports
import ktp_controller.api.client
import ktp_controller.examomatic.client
import ktp_controller.schemas
import ktp_controller.utils


@dataclasses.dataclass
class Try:
    done: bool = False
    nth: int | None = None


def tries(count: int = 0):
    try_ = Try()
    for i in range(count):
        try_.nth = i + 1
        yield try_
        if try_.done:
            break
        if i < count:
            time.sleep(1)
    assert try_.done


def assert_response(response, *, expected_status_code: int):
    try:
        assert response.status_code == expected_status_code
    except AssertionError:
        print(response.content, file=sys.stderr)
        raise


class Gender(str, enum.Enum):
    FEMALE = "female"
    MALE = "male"


HETU_CHECK_CHARS = "0123456789ABCDEFHJKLMNPRSTUVWXY"


# https://en.wikipedia.org/wiki/National_identification_number#Finland
# https://www.tuomas.salste.net/doc/tunnus/henkilotunnus.html#keinotunnus
def random_artificial_hetu(gender: Gender | None = None):
    if gender is None:
        range_step = 1  # Whole zzz value space is used.
    else:
        Gender(gender)
        range_step = 2  # Only half of the zzz value space is used.

    zzz = random.randrange(901 if gender == Gender.MALE else 900, 1000, range_step)

    now_date = datetime.datetime.now().date()

    # By default, we want to generate artificial hetus for
    # reasonable young testers, because they are assumed to be
    # Abitti2 students.
    min_birthday = now_date - datetime.timedelta(days=18 * 365)
    max_birthday = now_date - datetime.timedelta(days=7 * 365)

    birthday = min_birthday + datetime.timedelta(
        days=random.randrange(0, (max_birthday - min_birthday).days)
    )

    if birthday.year < 1800:
        raise RuntimeError("mummys cannot have hetus")
    if birthday.year < 1900:
        c = "+"  # They are all dead.
    elif birthday.year < 2000:
        c = "-"
    elif birthday.year < 2100:
        c = "A"
    else:
        raise RuntimeError("future is here")

    ddmmyy = birthday.strftime("%d%m%y")

    q = HETU_CHECK_CHARS[int(f"{ddmmyy}{zzz}") % 31]

    return f"{ddmmyy}{c}{zzz}{q}"


def assert_status_report_is_fresh(status_report, max_age_secs: int = 30) -> bool:
    return (
        ktp_controller.utils.utcnow()
        - datetime.datetime.fromisoformat(status_report["created_at"])
    ).total_seconds() <= max_age_secs


def assert_agent_has_called_home(*, gt: int = 0, wait: int = 5):
    if gt < 0:
        raise ValueError("invalid gt, must be >= 0", gt)
    if wait < 0:
        raise ValueError("invalid wait, must be >= 0", wait)

    for try_ in tries(wait + 1):
        state = ktp_controller.examomatic.client._post("/mock/get_state").json()
        if state["pong_count"] > gt:
            try_.done = True


def assert_agent_has_reported_status(*, gt: int = 0, wait: int = 15):
    if gt < 0:
        raise ValueError("invalid gt, must be >= 0", gt)
    if wait < 0:
        raise ValueError("invalid wait, must be >= 0", wait)

    # Check that we have received at least one status report from
    # the agent. It's a sign that Abitti2 is at least somewhat
    # healthy.
    for try_ in tries(wait + 1):
        state = ktp_controller.examomatic.client._post("/mock/get_state").json()
        status_reports = state["status_reports"]
        if len(status_reports) > 0:
            try_.done = True
            assert_status_report_is_fresh(status_reports[-1])


def assert_agent_has_done_initial_spontaneous_exam_refresh(
    *, wait: int = 15
) -> list[int]:
    if wait < 0:
        raise ValueError("invalid wait, must be >= 0", wait)

    for try_ in tries(wait + 1):
        state = ktp_controller.examomatic.client._post("/mock/get_state").json()
        get_exam_packages_status_codes = [
            s for p, s in state["requests"] if p == "/v2/schedules/exam_packages"
        ]
        if get_exam_packages_status_codes:
            try_.done = True
            # Refreshs must have been spontaneous, e.g. Exam-O-Matic did not
            # send refresh_exams message to Agent.
            assert state["refresh_exams_count"] == state["ack_count"] == 0

            # 404, because freshly started Exam-O-Matic does not have any
            # scheduled exams.
            assert get_exam_packages_status_codes == [404]


def assert_student_access_code_is(
    key_code, verification_code
) -> ktp_controller.schemas.StudentAccessCode:
    student_access_code = ktp_controller.api.client.get_student_access_code()
    assert student_access_code is not None
    assert (
        student_access_code.key_code,
        student_access_code.verification_code,
    ) == (
        key_code,
        verification_code,
    )
    return student_access_code


def assert_student_access_code_is_not(
    key_code, verification_code
) -> ktp_controller.schemas.StudentAccessCode:
    student_access_code = ktp_controller.api.client.get_student_access_code()
    assert student_access_code is not None
    assert (
        student_access_code.key_code,
        student_access_code.verification_code,
    ) != (
        "1234",
        "xx",
    )
    return student_access_code


def assert_abitti2_running_exams(cond: Callable[[list[str]], bool], *, wait: int = 5):
    if wait < 0:
        raise ValueError("invalid wait, must be >= 0", wait)

    for try_ in tries(wait + 1):
        state = ktp_controller.examomatic.client._post("/mock/get_state").json()
        status_reports = state["status_reports"]
        started_exam_titles = [
            e["title"]
            for e in status_reports[-1]["abitti2"]["exams"]
            if e["started_at"] is not None
        ]
        if cond(started_exam_titles):
            try_.done = True


def assert_clean_start() -> ktp_controller.schemas.StudentAccessCode:
    ktp_controller.abitti2.client.reset()
    assert_agent_has_called_home()
    assert_agent_has_done_initial_spontaneous_exam_refresh()
    assert_agent_has_reported_status()
    assert_api_has_copy_of_last_status_report()
    assert_abitti2_running_exams(
        lambda running_exams: "Odotusaulakoe" in running_exams, wait=30
    )
    return assert_student_access_code_is("1234", "xx")


def assert_api_has_copy_of_last_status_report():
    last_status_report_seen_by_api = ktp_controller.api.client.get_last_status_report()
    assert last_status_report_seen_by_api.pop("reported_at") is not None
    state = ktp_controller.examomatic.client._post("/mock/get_state").json()
    assert last_status_report_seen_by_api in state["status_reports"]


def assert_last_status_report_has_abitti2_domain():
    last_status_report_seen_by_api = ktp_controller.api.client.get_last_status_report()
    assert (
        last_status_report_seen_by_api["abitti2"]["domain"]
        == ktp_controller.abitti2.naksu2.read_domain()
    )
    assert last_status_report_seen_by_api["abitti2"]["domain"].endswith(
        ".koe.abitti.net"
    )


def assert_exam_scheduling_and_download(
    *,
    exam_title: str,
    seconds_until_start: int,
    duration_seconds: int,
    lock_time_duration_seconds: int,
    expected_ack_count: int,
    utcnow: datetime.datetime | None = None,
):
    if utcnow is None:
        utcnow = ktp_controller.utils.utcnow()
    response = ktp_controller.examomatic.client._post(
        "/mock/set_exam_info",
        json={
            "exam_title": exam_title,
            "start_time": (
                utcnow + datetime.timedelta(seconds=seconds_until_start)
            ).isoformat(),
            "duration_seconds": duration_seconds,
            "lock_time_duration_seconds": lock_time_duration_seconds,
        },
    )
    assert response.status_code == 200

    # Wait until Agent has refreshed exams (should happen almost
    # instantly since examomatic-mock sends refresh message via
    # websocket). The last exam data request is expected to be 200,
    # because an exam was just scheduled and Agent should have been
    # notified about it via websocket and Agent should have downloaded
    # the new exam data successfully.
    agent_downloaded_new_exam_info = False
    for i in range(10):
        state = ktp_controller.examomatic.client._post("/mock/get_state").json()

        get_exam_info_status_codes = [
            s for p, s in state["requests"] if p == "/v2/schedules/exam_packages"
        ]
        if get_exam_info_status_codes[-1] == 200:
            agent_downloaded_new_exam_info = True
            break
        time.sleep(1)
    assert agent_downloaded_new_exam_info

    # Now Exam-O-Matic has notified Agent and Agent has ack'd the
    # message. Note that ack comes from agent AFTER it has requested
    # exam info successfully, hence this small timeout after checking
    # ack.
    ackd = False
    for i in range(3):
        state = ktp_controller.examomatic.client._post("/mock/get_state").json()
        if state["refresh_exams_count"] == state["ack_count"] == expected_ack_count:
            ackd = True
        time.sleep(1)
    assert ackd


def assert_scheduled_exam_package_state_is(
    state: str,
    *,
    external_id: str,
    wait: int = 60,
) -> dict:
    if wait < 0:
        raise ValueError("invalid wait, must be >= 0", wait)

    scheduled_exam_package = None
    for try_ in tries(wait + 1):
        scheduled_exam_package = ktp_controller.api.client.get_scheduled_exam_package(
            external_id
        )
        if scheduled_exam_package["state"] == state:
            try_.done = True

    assert scheduled_exam_package is not None
    return scheduled_exam_package


def assert_scheduled_exam_package_gets_started(
    exam_title: str, wait: int = 120, utcnow: datetime.datetime | None = None
) -> dict:
    if utcnow is None:
        utcnow = ktp_controller.utils.utcnow()

    assert_abitti2_running_exams(
        lambda running_exams: exam_title in running_exams, wait=wait
    )

    current_exam_package = ktp_controller.api.client.get_current_exam_package()
    assert current_exam_package["state"] == "running"

    last_status_report_seen_by_api = ktp_controller.api.client.get_last_status_report()
    assert last_status_report_seen_by_api.pop("reported_at") is not None
    current_exam_package_from_status_report = last_status_report_seen_by_api[
        "ktp_controller"
    ].get("current_exam_package")
    assert current_exam_package_from_status_report is not None
    assert current_exam_package_from_status_report["state"] == "running"
    assert current_exam_package_from_status_report["archived_at"] is None
    assert (
        datetime.datetime.fromisoformat(
            current_exam_package_from_status_report["started_at"]
        )
        > utcnow
    )

    return current_exam_package


def assert_last_status_report_does_not_contain_student_names(*students):
    found_some_students = False
    for i in range(10):
        last_status_report_seen_by_api = (
            ktp_controller.api.client.get_last_status_report()
        )
        if len(last_status_report_seen_by_api["abitti2"]["students"]) > 1:
            found_some_students = True
            break
        time.sleep(1)
    assert found_some_students

    last_status_report_as_string = json.dumps(last_status_report_seen_by_api)

    for student in students:
        # Names of our students must not be found from the raw status
        # reports. We do string-based testing for these fields to ensure
        # this assertion holds even if Abitti2 decides to rename fields
        # which convey student name information. Because internally, we do
        # not process name fields nor check if they exist in reports sent
        # by Abitti2. This string-based checking can be replaced with
        # field/structure-based checking when/if Abitti2 status reports
        # strictly checked when received. See _Abitti2BaseModel in
        # ktp_controller/abitti2/schemas.py.
        assert (
            re.search(re.escape(student.last_name), last_status_report_as_string)
            is None
        )
        assert (
            re.search(re.escape(student.first_name), last_status_report_as_string)
            is None
        )


def assert_all_answer_uploads_are_successful():
    upload_answers_file_status_codes = []
    state = ktp_controller.examomatic.client._post("/mock/get_state").json()
    upload_answers_file_status_codes = [
        s for p, s in state["requests"] if p == "/v1/answers/upload"
    ]
    assert all(v == 200 for v in upload_answers_file_status_codes)
