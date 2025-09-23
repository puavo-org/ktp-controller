# Standard library imports
import json
import logging

# Internal imports
import ktp_controller.api.client
import ktp_controller.examomatic.client
import ktp_controller.utils


_LOGGER = logging.getLogger(__file__)


class ExamOMaticListener(ktp_controller.utils.Listener):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _open_websock(self):
        return ktp_controller.examomatic.client.open_websock()

    def __send_ping(self):
        self._send({"type": "ping"}, encoder=json.dumps)

    def __send_ack(self, message):
        self._send({"type": "ack", "id": message["id"]}, encoder=json.dumps)

    def _validate_message(self, message):
        try:
            message = json.loads(message)
        except Exception as e:
            raise ValueError("message is not JSON") from e

        if not isinstance(message, dict):
            raise ValueError("message is not a dict")

        if not "type" in message:
            raise ValueError("message does not have 'type'")

        if not isinstance(message["type"], str):
            raise ValueError("message type is not a string")

        if not "id" in message:
            raise ValueError("message does not have 'id'")

        if not isinstance(message["id"], int):
            raise ValueError("message id is not an integer")

        return message

    def _handle_validated_message(self, message):
        if message["type"] == "pong":
            return True

        self.__send_ack(message)

        if message["type"] == "change_keycode":
            _LOGGER.info("received change_keycode message from exam-o-matic")
            ktp_controller.api.client.change_keycode()
            return True

        if message["type"] == "refresh_exams":
            _LOGGER.info("received refresh_exams message from exam-o-matic")
            ktp_controller.api.client.sync_exams()
            return True

        return False

    def _on_alarm(self):
        self.__send_ping()


def run_listener():
    ExamOMaticListener(alarm_interval=30).run()
