# Standard library imports
import datetime
import time

# Third-party imports


# Internal imports
import ktp_controller.abitti2.client
import ktp_controller.api.client
import ktp_controller.examomatic.client


def test_single_exam_package():
    # 0. Reset Abitti2 to ensure it's in a well known state.
    ktp_controller.abitti2.client.reset()

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

    # 2. Check that Agent has tried initial exam refresh.
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

    # 3. Check that we have received at least one status report from
    # Abitti2. It's a sign that Abitti2 is at least somewhat
    # healthy.
    status_reports = []
    # First Abitti2 status report should not take long, Abitti2 seems
    # to send them once per 5secs.
    for i in range(5):
        state = ktp_controller.examomatic.client._post("/mock/get_state").json()
        status_reports = state["status_reports"]
        if len(status_reports) > 0:
            break
        time.sleep(1)
    # In the beginning, there were no exams running.
    assert not state["status_reports"][0]["status"]["data"]["examStatus"]["hasStarted"]

    # 4. Wait until Odotusaulakoe is running. (It takes some time
    # before Abitti2 gets the exam up and running after a reset.)
    odotusaulakoe_is_running = False
    for i in range(15):
        state = ktp_controller.examomatic.client._post("/mock/get_state").json()
        status_reports = state["status_reports"]
        if status_reports[-1]["status"]["data"]["examStatus"]["hasStarted"]:
            odotusaulakoe_is_running = True
            break
        time.sleep(1)
    assert odotusaulakoe_is_running

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
    # notified about it via websocket and Agent should have requested
    # downloaded the new exam data successfully.
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
    # Now Exam-O-Matic has notified Agent and Agent has ack'd the message.
    assert state["refresh_exams_count"] == state["ack_count"] == 1

    # 7. A small bonus goal: status reports are always saved by API,
    # so the last seen by API should also be reported to Exam-O-Matic.
    last_status_report_seen_by_api = (
        ktp_controller.api.client.get_last_abitti2_status_report()
    )
    assert last_status_report_seen_by_api.pop("reported_at") is not None
    state = ktp_controller.examomatic.client._post("/mock/get_state").json()
    assert last_status_report_seen_by_api in state["status_reports"]

    # Odotusaulakoe is still running.
    assert state["status_reports"][-1]["status"]["data"]["examStatus"]["hasStarted"]

    # Wait until it's not running anymore.
    exam_is_not_running = False
    for i in range(90):
        state = ktp_controller.examomatic.client._post("/mock/get_state").json()
        status_reports = state["status_reports"]
        if not status_reports[-1]["status"]["data"]["examStatus"]["hasStarted"]:
            exam_is_not_running = True
            break
        time.sleep(1)
    assert exam_is_not_running

    # And now wait until the scheduled exam is running.
    exam_is_running = False
    for i in range(15):
        state = ktp_controller.examomatic.client._post("/mock/get_state").json()
        status_reports = state["status_reports"]
        if status_reports[-1]["status"]["data"]["examStatus"]["hasStarted"]:
            exam_is_running = True
            break
        time.sleep(1)
    assert exam_is_running

    # TODO: use exam uuids or at least titles

    # 7. check status report which tells us if Abitti2 is ok (integration test exam ready)
    # 8. wait until start time
    # 9. check status report which tells us if Abitti2 is ok (integration test exam running)
    # 10. wait until end time
    # 11. check status report which tells us if Abitti2 is ok (integration test exam stopping)
    # 12. wait until exam is stopped completely
    # 13. check status report which tells us if Abitti2 is ok (integration test exam stopped)
    # 14. wait
    # 15. check status report which tells us if Abitti2 is ok (integration test exam archived)
    # 16. are exam answers still uploaded when there were no students? (student automation not included)
