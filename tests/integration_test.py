# Standard library imports
import datetime
import time

# Third-party imports


# Internal imports
import ktp_controller.abitti2.client
import ktp_controller.api.client
import ktp_controller.examomatic.client


# Test functions are and must be executed sequentially. In unit tests,
# it's not a good idea to build tests which depend on each other, but
# this is integration test scenario, and pytest is just a neat way to
# run them too. So, each test function is a sequential step in the
# testrun.


def _is_fresh_status_report(status_report, max_age_secs: int = 6) -> bool:
    return (
        ktp_controller.utils.utcnow()
        - datetime.datetime.fromisoformat(status_report["received_at"])
    ).total_seconds() <= max_age_secs


def test_abitti2_reset():
    # 0. Reset Abitti2 to ensure it's in a well known state.
    ktp_controller.abitti2.client.reset()


def test_first_examomatic_ping_pong():
    # 1. Wait until Agent has called home for the first time.
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
    # 2. Check that Agent has tried the initial exam refresh.
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


def test_abitti2_status_reporting():
    # 3. Check that we have received at least one status report from
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
    # 4. Wait until Odotusaulakoe is running. (It takes some time
    # before Abitti2 gets the exam up and running after a reset.)
    odotusaulakoe_is_running = False
    for i in range(15):
        state = ktp_controller.examomatic.client._post("/mock/get_state").json()
        status_reports = state["status_reports"]
        started_exam_titles = [
            e["examTitle"] for e in status_reports[-1]["exams"] if e["hasStarted"]
        ]
        if len(started_exam_titles) > 0:
            if "Odotusaulakoe" in started_exam_titles:
                odotusaulakoe_is_running = True
                break
        time.sleep(1)
    assert odotusaulakoe_is_running


def test_first_scheduled_exam_download():
    # 5. Prime examomatic-mock with exam info (single scheduled exam,
    # time intervals are short for testing purposes: 30sec pre-lock
    # time, 30sec lock time, 30 sec run time)
    utcnow = ktp_controller.utils.utcnow()
    response = ktp_controller.examomatic.client._post(
        "/mock/set_exam_info",
        json={
            "exam_title": "Integraatiotestikoe1",
            "start_time": (utcnow + datetime.timedelta(seconds=60)).isoformat(),
            "duration_seconds": 30,
            "lock_time_duration_seconds": 30,
        },
    )
    assert response.status_code == 200

    # 6. Wait until Agent has refreshed exams (should happen almost
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
        if state["refresh_exams_count"] == state["ack_count"] == 1:
            ackd = True
        time.sleep(1)
    assert ackd


def test_api_has_copies_of_status_reports():
    # 7. A small bonus goal: status reports are always stored by API,
    # so the last seen by API should also be reported to Exam-O-Matic.
    last_status_report_seen_by_api = (
        ktp_controller.api.client.get_last_abitti2_status_report()
    )
    assert last_status_report_seen_by_api.pop("reported_at") is not None
    state = ktp_controller.examomatic.client._post("/mock/get_state").json()
    assert last_status_report_seen_by_api in state["status_reports"]


def test_scheduled_exam_gets_started():
    # Odotusaulakoe is still running.
    last_status_report = ktp_controller.examomatic.client._post(
        "/mock/get_state"
    ).json()["status_reports"][-1]
    assert _is_fresh_status_report(last_status_report)
    assert "Odotusaulakoe" in [
        e["examTitle"] for e in last_status_report["exams"] if e["hasStarted"]
    ]

    # Wait until it's not running anymore.
    exam_package_is_not_running = False
    for i in range(90):
        state = ktp_controller.examomatic.client._post("/mock/get_state").json()
        status_reports = state["status_reports"]
        started_exam_titles = [
            e["examTitle"] for e in status_reports[-1]["exams"] if e["hasStarted"]
        ]
        if "Odotusaulakoe" not in started_exam_titles:
            exam_package_is_not_running = True
            break
        time.sleep(1)
    assert exam_package_is_not_running

    # And now wait until the scheduled exam package is running.
    exam_package_is_running = False
    for i in range(15):
        state = ktp_controller.examomatic.client._post("/mock/get_state").json()
        status_reports = state["status_reports"]
        started_exam_titles = [
            e["examTitle"] for e in status_reports[-1]["exams"] if e["hasStarted"]
        ]
        if "Integraatiotestikoe1" in started_exam_titles:
            exam_package_is_running = True
            break
        time.sleep(1)
    assert exam_package_is_running
    assert ktp_controller.api.client.get_current_exam_package()["state"] == "running"


def test_scheduled_exam_gets_stopped():
    # Wait until it's not running anymore.
    exam_package_is_not_running = False
    for i in range(90):
        scheduled_exam_package = ktp_controller.api.client.get_current_exam_package()
        if scheduled_exam_package["state"] == "stopped":
            exam_package_is_not_running = True
            break
        time.sleep(1)
    assert exam_package_is_not_running
