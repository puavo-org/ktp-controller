# Standard library imports
import datetime
import json
import re
import time

# Third-party imports

# Internal imports
import ktp_controller.abitti2.client
import ktp_controller.abitti2.naksu2
import ktp_controller.api.client
import ktp_controller.examomatic.client

# Relative imports

# Test functions are and must be executed sequentially. In unit tests,
# it's not a good idea to build tests which depend on each other, but
# this is integration test scenario, and pytest is just a neat way to
# run them too. So, each test function is a sequential step in the
# testrun.


scheduled_exam_package1 = None
scheduled_exam_package2 = None
student_access_code = None


def _assert_odotusaulakoe_is_running(timeout: int = 30):
    odotusaulakoe_is_running = False
    for i in range(timeout):
        state = ktp_controller.examomatic.client._post("/mock/get_state").json()
        status_reports = state["status_reports"]
        started_exam_titles = [
            e["title"]
            for e in status_reports[-1]["abitti2"]["exams"]
            if e["started_at"] is not None
        ]
        if len(started_exam_titles) > 0:
            if "Odotusaulakoe" in started_exam_titles:
                odotusaulakoe_is_running = True
                break
        time.sleep(1)
    assert odotusaulakoe_is_running


def _is_fresh_status_report(status_report, max_age_secs: int = 6) -> bool:
    return (
        ktp_controller.utils.utcnow()
        - datetime.datetime.fromisoformat(status_report["created_at"])
    ).total_seconds() <= max_age_secs


def test_abitti2_reset():
    # Reset Abitti2 to ensure it's in a well known state.
    ktp_controller.abitti2.client.reset()


def test_first_examomatic_ping_pong():
    # Wait until Agent has called home for the first time.
    agent_has_called_home = False
    # First ping-pong round should not take more than couple of
    # seconds.
    for i in range(5):
        state = ktp_controller.examomatic.client._post("/mock/get_state").json()
        if state["pong_count"] > 0:
            agent_has_called_home = True
            break
        time.sleep(1)
    assert agent_has_called_home


def test_initial_exam_refresh():
    # Check that Agent has tried the initial exam refresh.
    get_exam_packages_status_codes = []
    # It should happen right after the initial ping pong round.
    for i in range(5):
        state = ktp_controller.examomatic.client._post("/mock/get_state").json()
        get_exam_packages_status_codes = [
            s for p, s in state["requests"] if p == "/v2/schedules/exam_packages"
        ]
        if get_exam_packages_status_codes:
            break
        time.sleep(1)
    # 404, because freshly started Exam-O-Matic does not have any
    # scheduled exams.
    assert get_exam_packages_status_codes == [404]
    # And refresh exams was spontaneous, e.g. Exam-O-Matic did not
    # send refresh_exams message to Agent.
    assert state["refresh_exams_count"] == state["ack_count"] == 0


def test_status_reporting():
    # Check that we have received at least one status report from
    # Abitti2. It's a sign that Abitti2 is at least somewhat
    # healthy.
    status_reports = []
    # First Abitti2 status report should not take long, Abitti2 seems
    # to send them once per 5secs.
    for i in range(15):
        state = ktp_controller.examomatic.client._post("/mock/get_state").json()
        status_reports = state["status_reports"]
        if len(status_reports) > 0:
            break
        time.sleep(1)
    # Check that the last received status report is fresh.
    assert _is_fresh_status_report(status_reports[-1])


def test_odotusaulakoe_is_running():
    # Wait until Odotusaulakoe is running. (It takes some time
    # before Abitti2 gets the exam up and running after a reset.)
    _assert_odotusaulakoe_is_running(timeout=30)


def test_student_access_code_is_initially_1234_xx():
    global student_access_code
    student_access_code = ktp_controller.api.client.get_student_access_code()
    assert student_access_code is not None
    assert (student_access_code.key_code, student_access_code.verification_code) == (
        "1234",
        "xx",
    )


def test_student1_take_waiting_lobby_exam(student1):
    student1.load()
    student1.start_exam(
        exam_uuid="390e7988-ff0e-42b4-a2e6-d13a969e7103",
        exam_title="Odotusaulakoe",
        access_code=student_access_code,
    )
    student1.end_exam()


def test_student2_take_waiting_lobby_exam_but_do_not_end_it(student2):
    student2.load()
    student2.start_exam(
        exam_uuid="390e7988-ff0e-42b4-a2e6-d13a969e7103",
        exam_title="Odotusaulakoe",
        access_code=student_access_code,
    )


def test_first_scheduled_exam_download():
    # Prime examomatic-mock with exam info (single scheduled exam,
    # time intervals are short for testing purposes: 30sec pre-lock
    # time, 30sec lock time, 30 sec run time)
    utcnow = ktp_controller.utils.utcnow()
    response = ktp_controller.examomatic.client._post(
        "/mock/set_exam_info",
        json={
            "exam_title": "Ääkköskoe välilyönneillä integraatiotestaukseen",
            "start_time": (utcnow + datetime.timedelta(seconds=60)).isoformat(),
            "duration_seconds": 60,
            "lock_time_duration_seconds": 30,
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
        if state["refresh_exams_count"] == state["ack_count"] == 1:
            ackd = True
        time.sleep(1)
    assert ackd


def test_api_has_copies_of_status_reports():
    # A small bonus goal: status reports are always stored by API,
    # so the last seen by API should also be reported to Exam-O-Matic.
    last_status_report_seen_by_api = ktp_controller.api.client.get_last_status_report()
    assert last_status_report_seen_by_api.pop("reported_at") is not None
    state = ktp_controller.examomatic.client._post("/mock/get_state").json()
    assert last_status_report_seen_by_api in state["status_reports"]


def test_last_status_report_has_abitti2_domain():
    last_status_report_seen_by_api = ktp_controller.api.client.get_last_status_report()
    assert (
        last_status_report_seen_by_api["abitti2"]["domain"]
        == ktp_controller.abitti2.naksu2.read_domain()
    )
    assert last_status_report_seen_by_api["abitti2"]["domain"].endswith(
        ".koe.abitti.net"
    )


def test_first_scheduled_exam_gets_started():
    global scheduled_exam_package1

    # Odotusaulakoe is still running.
    last_status_report = ktp_controller.examomatic.client._post(
        "/mock/get_state"
    ).json()["status_reports"][-1]
    assert _is_fresh_status_report(last_status_report)
    assert "Odotusaulakoe" in [
        e["title"]
        for e in last_status_report["abitti2"]["exams"]
        if e["started_at"] is not None
    ]

    # Wait until it's not running anymore.
    exam_package_is_not_running = False
    for i in range(90):
        state = ktp_controller.examomatic.client._post("/mock/get_state").json()
        status_reports = state["status_reports"]
        started_exam_titles = [
            e["title"]
            for e in status_reports[-1]["abitti2"]["exams"]
            if e["started_at"] is not None
        ]
        if "Odotusaulakoe" not in started_exam_titles:
            exam_package_is_not_running = True
            break
        time.sleep(1)
    assert exam_package_is_not_running

    # And now wait until the scheduled exam package is running.
    exam_package_is_running = False
    for i in range(60):
        state = ktp_controller.examomatic.client._post("/mock/get_state").json()
        status_reports = state["status_reports"]
        started_exam_titles = [
            e["title"]
            for e in status_reports[-1]["abitti2"]["exams"]
            if e["started_at"] is not None
        ]
        if "Ääkköskoe välilyönneillä integraatiotestaukseen" in started_exam_titles:
            exam_package_is_running = True
            break
        time.sleep(1)
    assert exam_package_is_running

    scheduled_exam_package1 = ktp_controller.api.client.get_current_exam_package()

    assert scheduled_exam_package1["state"] == "running"


def test_student_access_code_is_changed_when_scheduled_exam_is_started():
    global student_access_code
    new_student_access_code = ktp_controller.api.client.get_student_access_code()
    assert new_student_access_code is not None
    assert new_student_access_code != student_access_code
    assert (
        new_student_access_code.key_code,
        new_student_access_code.verification_code,
    ) != ("1234", "xx")
    student_access_code = new_student_access_code


def test_student1_take_scheduled_exam(student1):
    student1.relogin()  # Exam has changed, relogin is needed.
    student1.start_exam(
        exam_uuid="53d3594c-cde8-43af-ae00-403ed134eba3",
        exam_title="Ääkköskoe välilyönneillä integraatiotestaukseen",
        access_code=student_access_code,
        expect_exam_instructions=False,  # Already seen in this browsing session, Abitti2 seems to show it only once.
    )
    student1.end_exam()


def test_student2_take_scheduled_exam_but_do_not_end_it(student2):
    student2.relogin()  # Exam has changed, relogin is needed.
    student2.start_exam(
        exam_uuid="53d3594c-cde8-43af-ae00-403ed134eba3",
        exam_title="Ääkköskoe välilyönneillä integraatiotestaukseen",
        access_code=student_access_code,
        expect_exam_instructions=False,  # Already seen in this browsing session, Abitti2 seems to show it only once.
    )


def test_status_reports_do_not_contain_student_names(student1, student2):
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
        re.search(re.escape(student1.last_name), last_status_report_as_string) is None
    )
    assert (
        re.search(re.escape(student1.first_name), last_status_report_as_string) is None
    )
    assert (
        re.search(re.escape(student2.last_name), last_status_report_as_string) is None
    )
    assert (
        re.search(re.escape(student2.first_name), last_status_report_as_string) is None
    )


def test_first_scheduled_exam_does_not_get_stopped_until_second_exam_is_locked(
    student2,
):
    global scheduled_exam_package1
    utcnow = ktp_controller.utils.utcnow()

    until_scheduled_end = (
        datetime.datetime.fromisoformat(scheduled_exam_package1["end_time"]) - utcnow
    ).total_seconds()
    time.sleep(until_scheduled_end + 10)

    scheduled_exam_package1 = ktp_controller.api.client.get_scheduled_exam_package(
        scheduled_exam_package1["external_id"]
    )
    assert scheduled_exam_package1["state"] == "running"  # Still running.

    # Prime examomatic-mock with exam info (single scheduled exam,
    # time intervals are short for testing purposes: 0sec pre-lock
    # time, 60sec lock time, 30 sec run time)
    utcnow = ktp_controller.utils.utcnow()
    response = ktp_controller.examomatic.client._post(
        "/mock/set_exam_info",
        json={
            "exam_title": "Integraatiotestikoe1",
            "start_time": (utcnow + datetime.timedelta(seconds=30)).isoformat(),
            "duration_seconds": 30,
            "lock_time_duration_seconds": 30,
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
    for i in range(2):
        state = ktp_controller.examomatic.client._post("/mock/get_state").json()
        if state["refresh_exams_count"] == state["ack_count"] == 2:
            ackd = True
        time.sleep(1)
    assert ackd

    # Wait until the first exam package is stopped.
    exam_package_is_stopped = False
    for i in range(30):
        scheduled_exam_package1 = ktp_controller.api.client.get_scheduled_exam_package(
            scheduled_exam_package1["external_id"]
        )
        if scheduled_exam_package1["state"] == "stopped":
            exam_package_is_stopped = True
            break
        time.sleep(1)
    assert exam_package_is_stopped


def test_first_scheduled_exam_gets_archived():
    global scheduled_exam_package1
    global scheduled_exam_package2

    # Wait until it's archived.
    exam_package_is_archived = False
    for i in range(90):
        scheduled_exam_package1 = ktp_controller.api.client.get_scheduled_exam_package(
            scheduled_exam_package1["external_id"]
        )
        if scheduled_exam_package1["state"] == "archived":
            exam_package_is_archived = True
            break
        time.sleep(1)
    assert exam_package_is_archived

    scheduled_exam_package2 = ktp_controller.api.client.get_current_exam_package()


def test_second_scheduled_exam_gets_archived():
    global scheduled_exam_package2

    # Wait until it's archived.
    exam_package_is_archived = False
    for i in range(90):
        scheduled_exam_package2 = ktp_controller.api.client.get_scheduled_exam_package(
            scheduled_exam_package2["external_id"]
        )
        if scheduled_exam_package2["state"] == "archived":
            exam_package_is_archived = True
            break
        time.sleep(1)
    assert exam_package_is_archived

    assert ktp_controller.api.client.get_current_exam_package() is None


def test_all_answer_uploads_are_successful():
    upload_answers_file_status_codes = []
    state = ktp_controller.examomatic.client._post("/mock/get_state").json()
    upload_answers_file_status_codes = [
        s for p, s in state["requests"] if p == "/v1/answers/upload"
    ]
    assert all(v == 200 for v in upload_answers_file_status_codes)


def test_odotusaulakoe_is_running_again():
    # Wait until Odotusaulakoe is running again. (It takes some time
    # before Abitti2 gets the exam up and running after a reset.)
    _assert_odotusaulakoe_is_running(timeout=30)
