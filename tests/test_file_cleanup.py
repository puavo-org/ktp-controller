import datetime
import os.path
import pathlib

import ktp_controller.files
import ktp_controller.utils


def _find_all_filepaths(basedir):
    filepaths = []
    for dirpath, _, filenames in os.walk(basedir):
        for filename in filenames:
            filepaths.append(os.path.join(dirpath, filename))
    return filepaths


def _find_all_dirpaths(basedir):
    dirpaths = []
    for dirpath, dirnames, _ in os.walk(basedir):
        for dirname in dirnames:
            dirpaths.append(os.path.join(dirpath, dirname))
    return dirpaths


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


def test_cleanup_old_archived_exam_package_dirs(testdir):
    basedir = os.path.join(
        testdir,
        f"test_cleanup_old_archived_exam_package_dirs_{ktp_controller.utils.utcnow_str()}.d",
    )

    # Monkey-patch for testing purposes.
    ktp_controller.files._EXAM_PACKAGE_DIR = os.path.join(basedir, "exam-packages")

    # One exam package per day, most recent first.
    exam_package_external_ids = [
        "8ee699fd-5183-4602-a081-8050194a2417",
        "711aee38-7a1f-43ed-a73e-8ebe2c083502",
        "0f0e003e-7619-4fe1-88e6-dfbf799c43e8",
        "a1fd78a4-fbb4-4e75-8939-ba20306c1724",
        "197c43e5-4635-49b4-ac0f-e805f44f292d",
        "c38c9bef-1533-4117-a369-47face03613e",
        "20141293-7241-40f3-a35a-dd2abfd3c870",
    ]

    for days_ago, exam_package_external_id in enumerate(exam_package_external_ids):
        dt = ktp_controller.utils.utcnow() - datetime.timedelta(days=days_ago)
        is_archived = (
            days_ago < 6
        )  # The oldest is not archived, expect it to not get deleted.
        exam_package_dirpath = ktp_controller.files.get_local_dirpath(
            ktp_controller.files.LocalFilepathType.EXAM_PACKAGE,
            exam_package_external_id,
        )
        if is_archived:
            with open(
                pathlib.Path(os.path.join(exam_package_dirpath, ".archived")),
                "w",
                encoding="utf-8",
            ) as archive_file:
                archive_file.write(ktp_controller.utils.strfdt(dt))
                archive_file.write("\n")

    exam_package_paths_BEFORE_cleanup = _find_all_dirpaths(basedir)
    exam_package_paths_BEFORE_cleanup.pop(0)  # The root dir is not interesting.

    # 7 exam packages
    assert len(exam_package_paths_BEFORE_cleanup) == len(exam_package_external_ids) == 7
    assert {pathlib.Path(p).name for p in exam_package_paths_BEFORE_cleanup} == set(
        exam_package_external_ids
    )

    deleted_exam_package_external_ids = set()
    ktp_controller.files.cleanup_archived_exam_packages(
        deleted_exam_package_external_ids=deleted_exam_package_external_ids
    )
    assert deleted_exam_package_external_ids == set(exam_package_external_ids) - set(
        [exam_package_external_ids[0], exam_package_external_ids[-1]]
    )  # Latest should not be deleted.

    exam_package_paths_AFTER_cleanup = _find_all_dirpaths(basedir)
    exam_package_paths_AFTER_cleanup.pop(0)  # The root dir is not interesting.

    # After cleanup
    # - the latest exam package still exists because archiving does not cleanup recently archived packages
    # - the oldest exam package still exists because it was not archived at all
    assert len(exam_package_paths_AFTER_cleanup) == 2
    assert {pathlib.Path(p).name for p in exam_package_paths_AFTER_cleanup} == set(
        [exam_package_external_ids[0], exam_package_external_ids[-1]]
    )
