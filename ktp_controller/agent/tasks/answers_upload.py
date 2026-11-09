# Standard library imports
import pathlib

# Internal imports
import ktp_controller.agent.answers
import ktp_controller.agent.tasks.base as base
import ktp_controller.files

__all__ = [
    "AnswersUploadTask",
]


async def _upload_one_pending_answers_file() -> None:
    answers_file_dir_path = pathlib.Path(ktp_controller.files.ANSWERS_FILE_DIR)

    # Latest answers file first, hence reverse=True. Filenames
    # contain naturally sorting ISO timestamps.
    for answers_file_path in sorted(
        answers_file_dir_path.glob("*/*.meb"), key=(lambda p: p.name), reverse=True
    ):
        uploaded = await ktp_controller.agent.answers.upload_answers_file(
            answers_file_path
        )
        if uploaded:
            # One at a time, this function will be called soon
            # again.
            break


class AnswersUploadTask:
    def __init__(self, *, interval_sec: int) -> None:
        self.__interval_sec = interval_sec

    async def run_ticker(self) -> None:
        await base.periodic(
            "answers file upload",
            self.__interval_sec,
            _upload_one_pending_answers_file,
            on_error_message="answers file upload failed",
        )
