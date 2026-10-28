# Standard library imports
import datetime

# Third-party imports
import httpx2 as httpx

# Internal imports
import ktp_controller.examomatic.client
import ktp_controller.utils


async def set_exam_info(
    *,
    exam_title: str,
    seconds_until_start: int = 30,
    duration_seconds: int = 15 * 60,
    lock_time_duration_seconds: int = 30,
    utcnow: datetime.datetime | None = None,
    number_of_duplicates: int = 0,
) -> httpx.Response:
    if utcnow is None:
        utcnow = ktp_controller.utils.utcnow()
    return await ktp_controller.examomatic.client._post(
        "/mock/set_exam_info",
        json={
            "exam_title": exam_title,
            "start_time": (
                utcnow + datetime.timedelta(seconds=seconds_until_start)
            ).isoformat(),
            "duration_seconds": duration_seconds,
            "lock_time_duration_seconds": lock_time_duration_seconds,
            "number_of_duplicates": number_of_duplicates,
        },
    )
