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

    # 1. wait until agent has called home for the first time
    # 1. check status report which tells us if Abitti2 is ok (dummy exam running)
    # 1. prime examomatic-mock with exam info
    # 1. wait until agent has called home
    # 1. check status report which tells us if Abitti2 is ok (integration test exam ready)
    # 1. wait until agent has called home
    # 1. check status report which tells us if Abitti2 is ok (integration test exam running)
    # 1. wait until agent has called home
    # 1. check status report which tells us if Abitti2 is ok (integration test exam stopping)
    # 1. wait until agent has called home
    # 1. check status report which tells us if Abitti2 is ok (integration test exam stopped)
    # 1. wait until agent has called home
    # 1. check status report which tells us if Abitti2 is ok (integration test exam archived)

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
