import datetime
import os.path
import pathlib

import ktp_controller.files
import ktp_controller.utils


def _find_all_filepaths(basedir):
    filepaths = []
    for dirpath, dirnames, filenames in os.walk(basedir):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            filepaths.append(filepath)
    return filepaths


def test_cleanup_old_answers_files(testdir):
    basedir = os.path.join(
        testdir,
        f"test_cleanup_old_answers_files_{ktp_controller.utils.utcnow_str()}.d",
    )

    # Monkey-patch for testing purposes.
    ktp_controller.files._ANSWERS_FILE_DIR = os.path.join(basedir, "answers-files")
    ktp_controller.files._ORPHAN_ANSWERS_FILE_DIR = os.path.join(
        basedir, "orphan-answers-files"
    )

    # One exam package per week, most recent first.
    exam_package_external_ids = [
        "8ee699fd-5183-4602-a081-8050194a2417",
        "711aee38-7a1f-43ed-a73e-8ebe2c083502",
        "0f0e003e-7619-4fe1-88e6-dfbf799c43e8",
        "a1fd78a4-fbb4-4e75-8939-ba20306c1724",
        "197c43e5-4635-49b4-ac0f-e805f44f292d",
        "c38c9bef-1533-4117-a369-47face03613e",
        "20141293-7241-40f3-a35a-dd2abfd3c870",
    ]

    for weeks_ago, exam_package_external_id in enumerate(exam_package_external_ids):
        dt = ktp_controller.utils.utcnow() - datetime.timedelta(weeks=weeks_ago)
        is_final = bool(weeks_ago % 2)
        suffix = ktp_controller.utils.strfdt(dt) + ("_final" if is_final else "")
        answers_file_path = ktp_controller.files.get_local_filepath(
            ktp_controller.files.LocalFilepathType.ANSWERS_FILE,
            exam_package_external_id,
            suffix,
        )
        pathlib.Path(answers_file_path).touch()
        orphan_answers_file_path = ktp_controller.files.get_local_filepath(
            ktp_controller.files.LocalFilepathType.ORPHAN_ANSWERS_FILE,
            exam_package_external_id,
            suffix,
        )
        pathlib.Path(orphan_answers_file_path).touch()

    answers_file_paths_BEFORE_cleanup = _find_all_filepaths(basedir)

    # 7 exam packages, each have one answers file + one orphan answers file
    assert len(answers_file_paths_BEFORE_cleanup) == len(exam_package_external_ids) * 2
    assert {
        pathlib.Path(p).parent.name for p in answers_file_paths_BEFORE_cleanup
    } == set(exam_package_external_ids)

    ktp_controller.files.cleanup_old_answers_files()

    answers_file_paths_AFTER_cleanup = _find_all_filepaths(basedir)

    # After cleanup, only answers from the last two weeks are left.
    assert len(answers_file_paths_AFTER_cleanup) == 2 * 2
    assert {
        pathlib.Path(p).parent.name for p in answers_file_paths_AFTER_cleanup
    } == set(exam_package_external_ids[:2])
