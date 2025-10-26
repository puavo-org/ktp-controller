# Standard library imports

# Third-party imports
import fastapi

# Internal imports
import ktp_controller.messages

# Relative imports
from .utils import client, testdb, db_engine, utcnow, assert_response

# Each test function executes in a separate session, each session
# starts with an empty database.


def test_enable_auto_control(client: fastapi.testclient.TestClient, testdb, utcnow):
    with client.websocket_connect("/api/v1/agent/websocket") as agent_websock:
        response = client.post("/api/v1/ui/async_enable_auto_control")
        assert_response(response, expected_status_code=202)
        data = agent_websock.receive_json()
        ktp_controller.messages.CommandMessage.model_validate(data)

        data.pop("uuid")
        assert data == {
            "kind": "command",
            "data": {
                "command": "enable_auto_control",
            },
        }


def test_disable_auto_control(client: fastapi.testclient.TestClient, testdb, utcnow):
    with client.websocket_connect("/api/v1/agent/websocket") as agent_websock:
        response = client.post("/api/v1/ui/async_disable_auto_control")
        assert_response(response, expected_status_code=202)
        data = agent_websock.receive_json()
        ktp_controller.messages.CommandMessage.model_validate(data)

        data.pop("uuid")
        assert data == {
            "kind": "command",
            "data": {
                "command": "disable_auto_control",
            },
        }
