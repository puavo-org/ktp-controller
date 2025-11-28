# Standard library imports
import datetime
import time

# Third-party imports


# Internal imports
import ktp_controller.abitti2.client
import ktp_controller.examomatic.client


def test_single_exam_package():
    utcnow = ktp_controller.utils.utcnow()

    # 0. Reset everything
    ktp_controller.abitti2.client.reset()

    # 1. wait until agent has called home for the first time
    agent_has_called_home = False
    for i in range(15):  # First ping-pong round should not take more than 15secs.
        state = ktp_controller.examomatic.client._post("/mock/get_state").json()
        if state["pong_count"] > 1:
            agent_has_called_home = True
            break
        time.sleep(1)
    assert agent_has_called_home

    # 2. check status report which tells us if Abitti2 is ok (dummy exam running)
    agent_has_sent_status_report = False
    for i in range(
        15
    ):  # First Abitti2 status report should not take long, Abitti2 seems to send them once per 5secs.
        state = ktp_controller.examomatic.client._post("/mock/get_state").json()
        if len(state["status_reports"]) > 0:
            agent_has_sent_status_report = True
            break
        time.sleep(1)
    assert agent_has_sent_status_report
    assert state["refresh_exams_count"] == state["ack_count"] == 0
    assert [s for p, s in state["requests"] if p == "/v2/schedules/exam_packages"] == [
        404,
        404,
    ]

    # 3. prime examomatic-mock with exam info (single scheduled exam, time intervals are short for testing purposes: 30sec pre-lock time, 30sec lock time, 30 sec run time)
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

    # 4. wait until agent has refreshed exams (should happen almost instantly since examomatic-mock sends refresh message via websocket)
    # The last exam data request is expected to be 200, because an
    # exam was just scheduled and the agent should have been notified
    # via websocket and the agent should have requested the new exam
    # data successfully.
    agent_received_new_exam_info = False
    for i in range(30):
        state = ktp_controller.examomatic.client._post("/mock/get_state").json()

        get_exam_info_status_codes = [
            s for p, s in state["requests"] if p == "/v2/schedules/exam_packages"
        ]
        if get_exam_info_status_codes[-1] == 200:
            agent_received_new_exam_info = True
            break
        time.sleep(1)
    assert agent_received_new_exam_info
    # assert state["refresh_exams_count"] == state["ack_count"] == 1

    # 5. check status report which tells us if Abitti2 is ok (integration test exam ready)
    # 6. wait until start time
    # 7. check status report which tells us if Abitti2 is ok (integration test exam running)
    # 8. wait until end time
    # 9. check status report which tells us if Abitti2 is ok (integration test exam stopping)
    # 10. wait until exam is stopped completely
    # 11. check status report which tells us if Abitti2 is ok (integration test exam stopped)
    # 12. wait
    # 13. check status report which tells us if Abitti2 is ok (integration test exam archived)
    # 14. are exam answers still uploaded when there were no students? (student automation not included)
