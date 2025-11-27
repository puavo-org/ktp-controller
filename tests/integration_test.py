# Standard library imports
import datetime
import time

# Third-party imports
import requests.exceptions

# Internal imports
import ktp_controller.examomatic.client
from ktp_controller.settings import SETTINGS


def test_single_exam_package():
    utcnow = datetime.datetime.utcnow()

    # 0. spawn all services (examomatic-mock, api, agent)
    # 1. wait until agent has called home for the first time
    # 2. check status report which tells us if Abitti2 is ok (dummy exam running)
    # 3. prime examomatic-mock with exam info (single scheduled exam, time intervals are short for testing purposes: 30sec pre-lock time, 30sec lock time, 30 sec run time)
    # 4. wait until agent has refreshed exams (should happen almost instantly since examomatic-mock sends refresh message via websocket)
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

    agent_has_called_home = False
    for i in range(15):  # First ping-pong round should not take more than 15sec
        state = ktp_controller.examomatic.client._post("/mock/get_state").json()
        if state["pong_count"] > 1:
            agent_has_called_home = True
            break
        time.sleep(1)
    assert agent_has_called_home

    agent_has_sent_status_report = False
    for i in range(
        15
    ):  # First Abitti2 status report should not take long, Abitti2 seems to send them 1 per 5secs.
        state = ktp_controller.examomatic.client._post("/mock/get_state").json()
        if len(state["status_reports"]) > 0:
            agent_has_sent_status_report = True
            break
        time.sleep(1)
    assert agent_has_sent_status_report

    # ktp_controller.examomatic.client._post(
    #     "/mock/set_exam_info",
    #     json={
    #         "exam_title": "Integraatiotestikoe1",
    #         "start_time": start_time.isoformat(),
    #         "duration_seconds": 60,
    #         "lock_time_duration_seconds": 60,
    #     },
    # )
