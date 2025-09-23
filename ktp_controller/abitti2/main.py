# Standard library imports
import logging

# Internal imports
import ktp_controller.abitti2.client
import ktp_controller.api.client
import ktp_controller.utils


_LOGGER = logging.getLogger(__file__)


class Abitti2Listener(ktp_controller.utils.Listener):
    def __send_pong(self):
        self._send("pong", encoder=str)

    def _open_websock(self):
        return ktp_controller.abitti2.client.open_websock()

    def _validate_message(self, message):
        if message == "ping":
            return ("ping", message)

        message = ktp_controller.utils.json_loads_dict(message)

        # TODO: any dict is valid message, is it ok?

        return ("status", message)

    def _handle_validated_message(self, validated_message) -> bool:
        message_type, message = validated_message

        if message_type == "ping":
            self.__send_pong()
            return True

        if message_type == "status":
            ktp_controller.api.client.post_api_v1_abitti2_status(message)
            return True

        return False


def run_listener():
    Abitti2Listener().run()
