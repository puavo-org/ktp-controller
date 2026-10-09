import fcntl
import os
import os.path
import threading
import time

import pytest

import ktp_controller.utils


def test_open_atomic_write_creates_dest_file(testdir):
    dest_filepath = os.path.join(testdir, "dest.txt")

    with ktp_controller.utils.open_atomic_write(
        dest_filepath, encoding="utf-8"
    ) as dest_file:
        dest_file.write("hello")

    with open(dest_filepath, encoding="utf-8") as f:
        assert f.read() == "hello"


def test_open_atomic_write_replaces_existing_dest_file(testdir):
    dest_filepath = os.path.join(testdir, "dest.txt")
    with open(dest_filepath, "w", encoding="utf-8") as f:
        f.write("old")

    with ktp_controller.utils.open_atomic_write(
        dest_filepath, encoding="utf-8"
    ) as dest_file:
        dest_file.write("new")

    with open(dest_filepath, encoding="utf-8") as f:
        assert f.read() == "new"


def test_open_atomic_write_does_not_leave_tmp_file_behind(testdir):
    dest_filepath = os.path.join(testdir, "dest.txt")

    with ktp_controller.utils.open_atomic_write(
        dest_filepath, encoding="utf-8"
    ) as dest_file:
        dest_file.write("hello")

    assert os.listdir(testdir) == ["dest.txt"]


def test_open_atomic_write_fsyncs_written_data_before_commit(testdir, mocker):
    dest_filepath = os.path.join(testdir, "dest.txt")
    fsync_spy = mocker.spy(ktp_controller.utils.os, "fsync")

    with ktp_controller.utils.open_atomic_write(
        dest_filepath, encoding="utf-8"
    ) as dest_file:
        dest_file.write("hello")
        tmp_fd = dest_file.fileno()

    assert mocker.call(tmp_fd) in fsync_spy.call_args_list


def test_open_atomic_write_fsyncs_dest_dir_after_commit(testdir, mocker):
    dest_filepath = os.path.join(testdir, "dest.txt")
    open_spy = mocker.spy(ktp_controller.utils.os, "open")
    fsync_spy = mocker.spy(ktp_controller.utils.os, "fsync")

    with ktp_controller.utils.open_atomic_write(
        dest_filepath, encoding="utf-8"
    ) as dest_file:
        dest_file.write("hello")

    dir_open_calls = [
        call for call in open_spy.call_args_list if call.args == (testdir, os.O_RDONLY)
    ]
    assert len(dir_open_calls) == 1
    dir_fd = open_spy.spy_return
    assert mocker.call(dir_fd) in fsync_spy.call_args_list


def test_open_atomic_write_exclusive_fsyncs_dest_dir_after_commit(testdir, mocker):
    dest_filepath = os.path.join(testdir, "dest.txt")
    fsync_spy = mocker.spy(ktp_controller.utils.os, "fsync")

    with ktp_controller.utils.open_atomic_write(
        dest_filepath, exclusive=True, encoding="utf-8"
    ) as dest_file:
        dest_file.write("hello")
        tmp_fd = dest_file.fileno()

    with open(dest_filepath, encoding="utf-8") as f:
        assert f.read() == "hello"
    assert fsync_spy.call_count == 2
    assert mocker.call(tmp_fd) in fsync_spy.call_args_list


def _write_and_raise(dest_filepath):
    with ktp_controller.utils.open_atomic_write(
        dest_filepath, encoding="utf-8"
    ) as dest_file:
        dest_file.write("new")
        raise RuntimeError("boom")


def test_open_atomic_write_does_not_touch_dest_file_on_error(testdir):
    dest_filepath = os.path.join(testdir, "dest.txt")
    with open(dest_filepath, "w", encoding="utf-8") as f:
        f.write("old")

    with pytest.raises(RuntimeError):
        _write_and_raise(dest_filepath)

    with open(dest_filepath, encoding="utf-8") as f:
        assert f.read() == "old"
    assert os.listdir(testdir) == ["dest.txt"]


def test_open_atomic_write_exclusive_raises_if_dest_file_exists(testdir):
    dest_filepath = os.path.join(testdir, "dest.txt")
    with open(dest_filepath, "w", encoding="utf-8") as f:
        f.write("old")

    with pytest.raises(FileExistsError):
        with ktp_controller.utils.open_atomic_write(
            dest_filepath, exclusive=True, encoding="utf-8"
        ) as dest_file:
            dest_file.write("new")

    with open(dest_filepath, encoding="utf-8") as f:
        assert f.read() == "old"


def _write_with_racing_creator(dest_filepath):
    # Simulate a second, racing writer finishing first: it creates
    # dest_filepath while this writer is still inside the `with`
    # block, i.e. after open_atomic_write's upfront os.path.exists()
    # check already passed.
    with ktp_controller.utils.open_atomic_write(
        dest_filepath, exclusive=True, encoding="utf-8"
    ) as dest_file:
        dest_file.write("new")
        with open(dest_filepath, "w", encoding="utf-8") as racer_file:
            racer_file.write("racer")


def test_open_atomic_write_exclusive_raises_if_dest_file_created_during_write(testdir):
    dest_filepath = os.path.join(testdir, "dest.txt")

    with pytest.raises(FileExistsError):
        _write_with_racing_creator(dest_filepath)

    with open(dest_filepath, encoding="utf-8") as f:
        assert f.read() == "racer"


def test_open_atomic_write_concurrent_writers_do_not_share_tmp_file(testdir):
    # Two overlapping open_atomic_write() calls for the same
    # dest_filepath must use distinct temp files. If they shared one
    # (keyed only on dest_filepath), the second writer's open(tmp, "x")
    # would fail, or a non-exclusive open would truncate/corrupt the
    # first writer's in-progress temp file and its final os.rename()
    # would then hit a FileNotFoundError, since the other writer
    # already renamed that path away.
    dest_filepath = os.path.join(testdir, "dest.txt")

    cm_a = ktp_controller.utils.open_atomic_write(dest_filepath, encoding="utf-8")
    dest_file_a = cm_a.__enter__()
    dest_file_a.write("a" * 10)
    dest_file_a.flush()

    cm_b = ktp_controller.utils.open_atomic_write(dest_filepath, encoding="utf-8")
    with cm_b as dest_file_b:
        dest_file_b.write("b" * 10)

    with open(dest_filepath, encoding="utf-8") as f:
        assert f.read() == "b" * 10

    cm_a.__exit__(None, None, None)

    with open(dest_filepath, encoding="utf-8") as f:
        assert f.read() == "a" * 10


def test_copy_atomic_copies_file_contents(testdir):
    src_filepath = os.path.join(testdir, "src.bin")
    dest_filepath = os.path.join(testdir, "dest.bin")
    with open(src_filepath, "wb") as f:
        f.write(b"\x00\x01binary-data" * 1000)

    ktp_controller.utils.copy_atomic(src_filepath, dest_filepath)

    with open(src_filepath, "rb") as f:
        src_data = f.read()
    with open(dest_filepath, "rb") as f:
        dest_data = f.read()
    assert dest_data == src_data


def test_copy_atomic_takes_shared_lock_on_src_file(testdir, mocker):
    src_filepath = os.path.join(testdir, "src.bin")
    dest_filepath = os.path.join(testdir, "dest.bin")
    with open(src_filepath, "wb") as f:
        f.write(b"data")

    flock_mock = mocker.patch("ktp_controller.utils.fcntl.flock")

    ktp_controller.utils.copy_atomic(src_filepath, dest_filepath)

    flock_mock.assert_called_once()
    (_lock_target, lock_op) = flock_mock.call_args.args
    assert lock_op == fcntl.LOCK_SH


def test_copy_atomic_waits_for_src_file_exclusive_lock_to_be_released(testdir):
    src_filepath = os.path.join(testdir, "src.bin")
    dest_filepath = os.path.join(testdir, "dest.bin")
    with open(src_filepath, "wb") as f:
        f.write(b"locked-content")

    def _release_lock_soon(lock_file):
        time.sleep(0.2)
        fcntl.flock(lock_file, fcntl.LOCK_UN)

    # flock() locks belong to the open file description, not the
    # process, so a second, independent open() of the same path
    # within this same test process still conflicts with this one.
    with open(src_filepath, "rb") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)

        releaser = threading.Thread(target=_release_lock_soon, args=(lock_file,))
        releaser.start()
        try:
            start = time.monotonic()
            ktp_controller.utils.copy_atomic(src_filepath, dest_filepath)
            elapsed = time.monotonic() - start
        finally:
            releaser.join()

    assert elapsed >= 0.2
    with open(dest_filepath, "rb") as f:
        assert f.read() == b"locked-content"
