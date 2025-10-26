# Standard library imports
import uuid

# Third-party imports

# Internal imports
import ktp_controller.redis
import ktp_controller.messages


PUBSUB_CHANNEL = f"ktp-controller__ui_messages__{ str(uuid.uuid4()) }"


async def send_status_report(
    status_repot_data: ktp_controller.messages.StatusReportData,
) -> str:
    status_report_message = ktp_controller.messages.StatusReportMessage(
        data=status_repot_data
    )
    return await ktp_controller.redis.pubsub_send(status_report_message, PUBSUB_CHANNEL)
