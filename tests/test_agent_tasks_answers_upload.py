import os.path
import pathlib

import pytest

import ktp_controller.agent.tasks.answers_upload as answers_upload
import ktp_controller.files


@pytest.mark.anyio
async def test_uploads_latest_pending_answers_file_and_stops(mocker, testdir):
    answers_file_dir_path = os.path.join(testdir, "answers-files")
    mocker.patch.object(ktp_controller.files, "ANSWERS_FILE_DIR", answers_file_dir_path)

    exam_package_dir_path = os.path.join(answers_file_dir_path, "exam-package")
    os.makedirs(exam_package_dir_path)

    older_path = pathlib.Path(exam_package_dir_path, "2024-01-01T00:00:00.meb")
    older_path.write_bytes(b"older")
    newer_path = pathlib.Path(exam_package_dir_path, "2024-01-02T00:00:00.meb")
    newer_path.write_bytes(b"newer")

    upload_mock = mocker.patch(
        "ktp_controller.agent.answers.upload_answers_file",
        return_value=True,
    )

    await answers_upload._upload_one_pending_answers_file()

    upload_mock.assert_awaited_once_with(newer_path)


@pytest.mark.anyio
async def test_tries_next_file_when_upload_is_skipped(mocker, testdir):
    answers_file_dir_path = os.path.join(testdir, "answers-files")
    mocker.patch.object(ktp_controller.files, "ANSWERS_FILE_DIR", answers_file_dir_path)

    exam_package_dir_path = os.path.join(answers_file_dir_path, "exam-package")
    os.makedirs(exam_package_dir_path)

    older_path = pathlib.Path(exam_package_dir_path, "2024-01-01T00:00:00.meb")
    older_path.write_bytes(b"older")
    newer_path = pathlib.Path(exam_package_dir_path, "2024-01-02T00:00:00.meb")
    newer_path.write_bytes(b"newer")

    upload_mock = mocker.patch(
        "ktp_controller.agent.answers.upload_answers_file",
        side_effect=[False, True],
    )

    await answers_upload._upload_one_pending_answers_file()

    assert upload_mock.await_args_list == [
        mocker.call(newer_path),
        mocker.call(older_path),
    ]
