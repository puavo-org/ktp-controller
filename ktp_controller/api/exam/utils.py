import typing

from ktp_controller.api import models
from . import schemas


def db_exam_file_info_to_dict(db_exam_file_info: models.ExamFileInfo) -> typing.Dict:
    return schemas.ExamFileInfo(
        external_id=db_exam_file_info.external_id,
        name=db_exam_file_info.name,
        size=db_exam_file_info.size,
        sha256=db_exam_file_info.sha256,
        decrypt_code=db_exam_file_info.decrypt_code,
        modified_at=db_exam_file_info.modified_at,
    ).dict()


def db_scheduled_exam_to_dict(db_scheduled_exam: models.ScheduledExam) -> typing.Dict:
    return schemas.ScheduledExam(
        external_id=db_scheduled_exam.external_id,
        exam_title=db_scheduled_exam.exam_title,
        start_time=db_scheduled_exam.start_time,
        end_time=db_scheduled_exam.end_time,
        modified_at=db_scheduled_exam.modified_at,
        exam_file_info=db_exam_info_to_dict(db_scheduled_exam.exam_info),
    ).dict()


def db_exam_info_to_dict(db_exam_info: models.ExamInfo) -> typing.Dict:
    return schemas.ExamInfo(
        request_id=db_exam_info.request_id,
        raw_data=db_exam_info.raw_data,
        scheduled_exams=[db_exam_info.raw_data["scheduled_exams"]],
        scheduled_exam_packages=[db_exam_info.raw_data["scheduled_exam_packages"]],
    ).dict()
