# Standard library imports
import collections
import datetime
import logging
import typing

# Internal imports
import ktp_controller.abitti2.utils
import ktp_controller.api.client
import ktp_controller.utils
import ktp_controller.wui.schemas

__all__ = [
    "get_student_list_items",
    "count_student_states",
    "get_student_state_labels",
]

_LOGGER = logging.getLogger(__name__)


async def get_student_list_items() -> list[ktp_controller.wui.schemas.StudentListItem]:
    utcnow = ktp_controller.utils.utcnow()

    raw_abitti2_stats_messages = (
        await ktp_controller.api.client.get_raw_abitti2_stats_messages()
    )
    if len(raw_abitti2_stats_messages) == 0:
        return []

    last_raw_abitti2_stats_message = raw_abitti2_stats_messages[0]

    try:
        raw_abitti2_students = last_raw_abitti2_stats_message["data"]["students"]
    except KeyError:
        return []

    audio_in_some_exam: bool = last_raw_abitti2_stats_message["data"].get(
        "audioInSomeExam", False
    )

    student_list_items = []

    for raw_abitti2_student in raw_abitti2_students:
        # TODO: What if studentBd does not exist or is invalid?
        birthday_ddmmyy: str = raw_abitti2_student["studentBd"]
        birthday: datetime.date = ktp_controller.utils.parse_ddmmyy(birthday_ddmmyy)
        state: str = raw_abitti2_student["studentStatus"]
        update_time: datetime.datetime | None = (
            datetime.datetime.fromisoformat(
                raw_abitti2_student["updateTime"]
            ).astimezone()
            if raw_abitti2_student["updateTime"] is not None
            else None
        )
        exam_finished_at: datetime.datetime | None = (
            datetime.datetime.fromisoformat(
                raw_abitti2_student["examFinishedAt"]
            ).astimezone()
            if raw_abitti2_student["examFinishedAt"] is not None
            else None
        )
        last_changed_at: datetime.datetime | None = None
        if update_time is None and exam_finished_at is None:
            last_changed_at = None
        elif update_time is not None and exam_finished_at is not None:
            last_changed_at = max(update_time, exam_finished_at)
        elif update_time is None:
            last_changed_at = exam_finished_at
        elif exam_finished_at is None:
            last_changed_at = update_time
        else:
            raise RuntimeError("impossible internal logic")

        exam_title: str = raw_abitti2_student["examTitle"]

        last_audio: int | None = (
            int(raw_abitti2_student.get("lastAccessedMedia") or 0)
            if audio_in_some_exam
            else None
        )

        state_info = ktp_controller.abitti2.utils.parse_student_state_info(
            raw_abitti2_student,
            utcnow=utcnow,
        )
        if state_info["has_finished"]:
            state = ktp_controller.wui.schemas.StudentState.FINISHED
        elif state_info["is_active"]:
            state = ktp_controller.wui.schemas.StudentState.IN_EXAM
        elif len(state_info["flags"]) > 0 and all(
            f.lower().startswith("waiting") for f in state_info["flags"]
        ):
            state = ktp_controller.wui.schemas.StudentState.WAITING
        else:
            state = ktp_controller.wui.schemas.StudentState.HAS_PROBLEMS

        student_list_item = ktp_controller.wui.schemas.StudentListItem(
            name=f"{raw_abitti2_student['lastName']}, {raw_abitti2_student['firstNames']}",
            birthday=birthday,
            state=state,
            flags=state_info["flags"],
            last_changed_at=last_changed_at,
            exam_title=exam_title,
            student_uuid=raw_abitti2_student["studentUuid"],
            session_uuid=raw_abitti2_student["sessionUuid"],
            is_allowed_to_use_browser=raw_abitti2_student.get(
                "isAllowedToUseBrowser", False
            ),
            last_audio=last_audio,
            wants_to_use_browser=raw_abitti2_student.get(
                "loginInitiatedOnBrowser", False
            ),
        )

        student_list_items.append(student_list_item)

    return student_list_items


def count_student_states(
    items: typing.Iterable[ktp_controller.wui.schemas.StudentListItem],
) -> dict[str, int]:
    return dict(
        ktp_controller.wui.schemas.StudentStateCounts(
            **dict(collections.Counter(item.state for item in items))
        )
    )


def get_student_state_labels(
    _: typing.Callable[[str], str],
) -> dict[ktp_controller.wui.schemas.StudentState, str]:
    # Insertion order is the the rendering order.
    return {
        ktp_controller.wui.schemas.StudentState.WAITING: _("Waiting"),
        ktp_controller.wui.schemas.StudentState.IN_EXAM: _("In exam"),
        ktp_controller.wui.schemas.StudentState.HAS_PROBLEMS: _("Has problems"),
        ktp_controller.wui.schemas.StudentState.FINISHED: _("Finished"),
    }
