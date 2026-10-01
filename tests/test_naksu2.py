import os.path

import pytest

import ktp_controller.abitti2.naksu2

ROTATED_AND_NONROTATED_LOG_FILENAMES = [
    "johdanto-rivitys.koe.abitti.net-docker.json",
    "johdanto-rivitys.koe.abitti.net-ktpjs.log",
    "johdanto-rivitys.koe.abitti.net-metrics-2026-09-26T18-17-14.425-size.json",
    "johdanto-rivitys.koe.abitti.net-metrics-2026-09-27T20-02-17.321-size.json",
    "johdanto-rivitys.koe.abitti.net-metrics.json",
    "johdanto-rivitys.koe.abitti.net-remove-old-logs-2026-09-30.log",
    "johdanto-rivitys.koe.abitti.net-remove-old-logs-2026-10-01.log",
    "johdanto-rivitys.koe.abitti.net-traces-2026-09-23T22-13-06.227-size.json",
    "johdanto-rivitys.koe.abitti.net-traces-2026-09-23T22-59-42.226-size.json",
    "johdanto-rivitys.koe.abitti.net-traces-2026-09-24T20-29-05.935-size.json",
    "johdanto-rivitys.koe.abitti.net-traces-2026-09-24T21-16-01.935-size.json",
    "johdanto-rivitys.koe.abitti.net-traces-2026-09-24T22-03-01.936-size.json",
    "johdanto-rivitys.koe.abitti.net-traces-2026-09-24T22-46-09.936-size.json",
    "johdanto-rivitys.koe.abitti.net-traces-2026-09-24T23-32-53.141-size.json",
    "johdanto-rivitys.koe.abitti.net-traces-2026-09-25T18-37-19.936-size.json",
    "johdanto-rivitys.koe.abitti.net-traces-2026-09-25T19-21-15.936-size.json",
    "johdanto-rivitys.koe.abitti.net-traces-2026-09-26T16-23-22.392-size.json",
    "johdanto-rivitys.koe.abitti.net-traces-2026-09-26T17-02-36.392-size.json",
    "johdanto-rivitys.koe.abitti.net-traces-2026-09-26T17-46-32.393-size.json",
    "johdanto-rivitys.koe.abitti.net-traces-2026-09-26T18-33-09.395-size.json",
    "johdanto-rivitys.koe.abitti.net-traces-2026-09-26T19-19-23.391-size.json",
    "johdanto-rivitys.koe.abitti.net-traces-2026-09-26T20-03-52.975-size.json",
    "johdanto-rivitys.koe.abitti.net-traces-2026-09-26T20-49-02.393-size.json",
    "johdanto-rivitys.koe.abitti.net-traces-2026-09-26T21-34-22.392-size.json",
    "johdanto-rivitys.koe.abitti.net-traces-2026-09-26T22-17-26.392-size.json",
    "johdanto-rivitys.koe.abitti.net-traces-2026-09-26T23-02-53.391-size.json",
    "johdanto-rivitys.koe.abitti.net-traces-2026-09-27T10-32-37.392-size.json",
    "johdanto-rivitys.koe.abitti.net-traces-2026-09-27T11-12-30.044-size.json",
    "johdanto-rivitys.koe.abitti.net-traces-2026-09-27T18-06-10.413-size.json",
    "johdanto-rivitys.koe.abitti.net-traces-2026-09-27T18-52-22.413-size.json",
    "johdanto-rivitys.koe.abitti.net-traces-2026-09-27T19-37-59.413-size.json",
    "johdanto-rivitys.koe.abitti.net-traces-2026-09-27T20-23-50.413-size.json",
    "johdanto-rivitys.koe.abitti.net-traces-2026-09-27T21-04-59.414-size.json",
    "johdanto-rivitys.koe.abitti.net-traces-2026-09-27T21-48-36.415-size.json",
    "johdanto-rivitys.koe.abitti.net-traces-2026-09-27T22-33-35.413-size.json",
    "johdanto-rivitys.koe.abitti.net-traces-2026-09-28T21-37-37.413-size.json",
    "johdanto-rivitys.koe.abitti.net-traces-2026-09-28T22-17-52.413-size.json",
    "johdanto-rivitys.koe.abitti.net-traces-2026-09-30T21-47-02.557-size.json",
    "johdanto-rivitys.koe.abitti.net-traces-2026-09-30T22-33-43.544-size.json",
    "johdanto-rivitys.koe.abitti.net-traces-2026-09-30T23-39-05.029-size.json",
    "johdanto-rivitys.koe.abitti.net-traces-2026-10-01T20-25-30.541-size.json",
    "johdanto-rivitys.koe.abitti.net-traces.json",
    "johdanto-rivitys-remove-old-logs-2026-09-30.log",
    "naksu2.log",
]

EXPECTED_SURVIVING_LOG_FILENAMES = {
    "johdanto-rivitys.koe.abitti.net-docker.json",
    "johdanto-rivitys.koe.abitti.net-ktpjs.log",
    "johdanto-rivitys.koe.abitti.net-metrics.json",
    "johdanto-rivitys.koe.abitti.net-remove-old-logs-2026-09-30.log",
    "johdanto-rivitys.koe.abitti.net-remove-old-logs-2026-10-01.log",
    "johdanto-rivitys.koe.abitti.net-traces.json",
    "johdanto-rivitys-remove-old-logs-2026-09-30.log",
    "naksu2.log",
}


def _populate_logs_dir(logs_dirpath, log_filenames):
    os.makedirs(logs_dirpath)
    for log_filename in log_filenames:
        open(os.path.join(logs_dirpath, log_filename), "w", encoding="utf-8").close()


def test_cleanup_rotated_logs_removes_only_rotated_logs(testdir):
    logs_dirpath = os.path.join(testdir, "logs")
    _populate_logs_dir(logs_dirpath, ROTATED_AND_NONROTATED_LOG_FILENAMES)

    deleted_log_filepaths = set()
    ktp_controller.abitti2.naksu2.cleanup_rotated_logs(
        logs_dirpath=logs_dirpath, deleted_log_filepaths=deleted_log_filepaths
    )

    assert set(os.listdir(logs_dirpath)) == EXPECTED_SURVIVING_LOG_FILENAMES

    expected_deleted_log_filenames = (
        set(ROTATED_AND_NONROTATED_LOG_FILENAMES) - EXPECTED_SURVIVING_LOG_FILENAMES
    )
    assert deleted_log_filepaths == {
        os.path.join(logs_dirpath, log_filename)
        for log_filename in expected_deleted_log_filenames
    }


def test_cleanup_rotated_logs_without_deleted_log_filepaths_arg(testdir):
    # deleted_log_filepaths is optional; the caller may not care about which
    # filepaths were actually deleted.
    logs_dirpath = os.path.join(testdir, "logs")
    _populate_logs_dir(logs_dirpath, ROTATED_AND_NONROTATED_LOG_FILENAMES)

    ktp_controller.abitti2.naksu2.cleanup_rotated_logs(logs_dirpath=logs_dirpath)

    assert set(os.listdir(logs_dirpath)) == EXPECTED_SURVIVING_LOG_FILENAMES


def test_cleanup_rotated_logs_is_noop_when_dir_is_missing(testdir):
    logs_dirpath = os.path.join(testdir, "does-not-exist")

    # Must not raise.
    ktp_controller.abitti2.naksu2.cleanup_rotated_logs(logs_dirpath=logs_dirpath)


def test_cleanup_rotated_logs_is_noop_when_dir_is_empty(testdir):
    logs_dirpath = os.path.join(testdir, "logs")
    os.makedirs(logs_dirpath)

    deleted_log_filepaths = set()
    ktp_controller.abitti2.naksu2.cleanup_rotated_logs(
        logs_dirpath=logs_dirpath, deleted_log_filepaths=deleted_log_filepaths
    )

    assert deleted_log_filepaths == set()
    assert os.listdir(logs_dirpath) == []


def test_cleanup_rotated_logs_matches_case_insensitively(testdir):
    logs_dirpath = os.path.join(testdir, "logs")
    rotated_log_filename = (
        "johdanto-rivitys.KOE.ABITTI.NET-traces-2026-09-23T22-13-06.227-SIZE.JSON"
    )
    _populate_logs_dir(logs_dirpath, [rotated_log_filename])

    deleted_log_filepaths = set()
    ktp_controller.abitti2.naksu2.cleanup_rotated_logs(
        logs_dirpath=logs_dirpath, deleted_log_filepaths=deleted_log_filepaths
    )

    assert os.listdir(logs_dirpath) == []
    assert deleted_log_filepaths == {os.path.join(logs_dirpath, rotated_log_filename)}


def test_cleanup_rotated_logs_raises_exception_group_on_failed_deletion(
    testdir, monkeypatch
):
    # cleanup_rotated_logs() is best-effort: a failure to delete one
    # rotated log file must not stop it from deleting the others, and the
    # successfully deleted ones must still be reported.
    logs_dirpath = os.path.join(testdir, "logs")
    failing_log_filename = (
        "johdanto-rivitys.koe.abitti.net-traces-2026-09-23T22-13-06.227-size.json"
    )
    succeeding_log_filenames = {
        "johdanto-rivitys.koe.abitti.net-traces-2026-09-24T20-29-05.935-size.json",
        "johdanto-rivitys.koe.abitti.net-metrics-2026-09-26T18-17-14.425-size.json",
    }
    _populate_logs_dir(logs_dirpath, [failing_log_filename, *succeeding_log_filenames])

    failing_log_filepath = os.path.join(logs_dirpath, failing_log_filename)
    real_unlink = os.unlink

    def _unlink_failing_one_file(filepath):
        if filepath == failing_log_filepath:
            raise OSError(f"permission denied: {filepath}")
        real_unlink(filepath)

    monkeypatch.setattr(os, "unlink", _unlink_failing_one_file)

    deleted_log_filepaths = set()
    with pytest.raises(ExceptionGroup) as exc_info:
        ktp_controller.abitti2.naksu2.cleanup_rotated_logs(
            logs_dirpath=logs_dirpath, deleted_log_filepaths=deleted_log_filepaths
        )
    assert len(exc_info.value.exceptions) == 1
    assert isinstance(exc_info.value.exceptions[0], OSError)

    # The file that failed to be deleted is still on disk and not reported
    # as deleted, but the other rotated log files were deleted and
    # reported despite that failure.
    assert os.listdir(logs_dirpath) == [failing_log_filename]
    assert deleted_log_filepaths == {
        os.path.join(logs_dirpath, log_filename)
        for log_filename in succeeding_log_filenames
    }


def test_cleanup_rotated_logs_default_logs_dirpath(monkeypatch, testdir):
    logs_dirpath = os.path.join(testdir, "logs")
    rotated_log_filename = (
        "johdanto-rivitys.koe.abitti.net-traces-2026-09-23T22-13-06.227-size.json"
    )
    _populate_logs_dir(logs_dirpath, [rotated_log_filename])

    monkeypatch.setattr(ktp_controller.abitti2.naksu2, "_NAKSU2_CONF_DIR_PATH", testdir)

    deleted_log_filepaths = set()
    ktp_controller.abitti2.naksu2.cleanup_rotated_logs(
        deleted_log_filepaths=deleted_log_filepaths
    )

    assert os.listdir(logs_dirpath) == []
    assert deleted_log_filepaths == {os.path.join(logs_dirpath, rotated_log_filename)}
