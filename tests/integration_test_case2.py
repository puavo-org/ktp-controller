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


scheduled_exam_package = None


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


def test_odotusaulakoe_is_running():
    # Wait until Odotusaulakoe is running. (It takes some time
    # before Abitti2 gets the exam up and running after a reset.)
    _assert_odotusaulakoe_is_running(timeout=30)


def test_first_scheduled_exam_download():
    # Prime examomatic-mock with exam info (single scheduled exam,
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
    for i in range(5):
        state = ktp_controller.examomatic.client._post("/mock/get_state").json()
        if state["refresh_exams_count"] == state["ack_count"] == 1:
            ackd = True
        time.sleep(1)
    assert ackd


def test_first_scheduled_exam_gets_started():
    global scheduled_exam_package

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
        if "Integraatiotestikoe1" in started_exam_titles:
            exam_package_is_running = True
            break
        time.sleep(1)
    assert exam_package_is_running

    scheduled_exam_package = ktp_controller.api.client.get_current_exam_package()

    assert scheduled_exam_package["state"] == "running"


def test_first_scheduled_exam_gets_stopped():
    global scheduled_exam_package

    # Wait until it's stopped.
    exam_package_is_stopped = False
    for i in range(90):
        scheduled_exam_package = ktp_controller.api.client.get_scheduled_exam_package(
            scheduled_exam_package["external_id"]
        )
        if scheduled_exam_package["state"] == "stopped":
            exam_package_is_stopped = True
            break
        time.sleep(1)
    assert exam_package_is_stopped


def test_first_scheduled_exam_gets_archived():
    global scheduled_exam_package

    # Wait until it's archived.
    exam_package_is_archived = False
    for i in range(90):
        scheduled_exam_package = ktp_controller.api.client.get_scheduled_exam_package(
            scheduled_exam_package["external_id"]
        )
        if scheduled_exam_package["state"] == "archived":
            exam_package_is_archived = True
            break
        time.sleep(1)
    assert exam_package_is_archived

    assert ktp_controller.api.client.get_current_exam_package() is None


def test_odotusaulakoe_is_running_between_exams():
    # Wait until Odotusaulakoe is running again. (It takes some time
    # before Abitti2 gets the exam up and running after a reset.)
    _assert_odotusaulakoe_is_running(timeout=30)


def test_second_scheduled_exam_download():
    # Prime examomatic-mock with exam info (single scheduled exam,
    # time intervals are short for testing purposes: 30sec pre-lock
    # time, 30sec lock time, 30 sec run time)
    utcnow = ktp_controller.utils.utcnow()
    response = ktp_controller.examomatic.client._post(
        "/mock/set_exam_info",
        json={
            "exam_title": "Integraatiotestikoe2",
            "start_time": (utcnow + datetime.timedelta(seconds=60)).isoformat(),
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
        if state["refresh_exams_count"] == state["ack_count"] == 1:
            ackd = True
        time.sleep(1)
    assert ackd


def test_second_scheduled_exam_gets_started():
    global scheduled_exam_package

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
        if "Integraatiotestikoe2" in started_exam_titles:
            exam_package_is_running = True
            break
        time.sleep(1)
    assert exam_package_is_running

    scheduled_exam_package = ktp_controller.api.client.get_current_exam_package()

    assert scheduled_exam_package["state"] == "running"


def test_second_scheduled_exam_gets_stopped():
    global scheduled_exam_package

    # Wait until it's stopped.
    exam_package_is_stopped = False
    for i in range(90):
        scheduled_exam_package = ktp_controller.api.client.get_scheduled_exam_package(
            scheduled_exam_package["external_id"]
        )
        if scheduled_exam_package["state"] == "stopped":
            exam_package_is_stopped = True
            break
        time.sleep(1)
    assert exam_package_is_stopped


def test_second_scheduled_exam_gets_archived():
    global scheduled_exam_package

    # Wait until it's archived.
    exam_package_is_archived = False
    for i in range(90):
        scheduled_exam_package = ktp_controller.api.client.get_scheduled_exam_package(
            scheduled_exam_package["external_id"]
        )
        if scheduled_exam_package["state"] == "archived":
            exam_package_is_archived = True
            break
        time.sleep(1)
    assert exam_package_is_archived

    assert ktp_controller.api.client.get_current_exam_package() is None


def test_odotusaulakoe_is_running_at_the_end():
    # Wait until Odotusaulakoe is running again. (It takes some time
    # before Abitti2 gets the exam up and running after a reset.)
    _assert_odotusaulakoe_is_running(timeout=30)
