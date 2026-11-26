import logging
import os
import pathlib

import ktp_controller.files
import ktp_controller.utils


def _find_all_dirpaths(basedir):
    dirpaths = []
    for dirpath, dirnames, _ in os.walk(basedir):
        dirpaths.extend(os.path.join(dirpath, dirname) for dirname in dirnames)
    return dirpaths


def _setup_dirs(testdir, monkeypatch):
    basedir = os.path.join(
        testdir,
        f"test_migrate_legacy_data_dirs_{ktp_controller.utils.utcnow_str()}.d",
    )
    legacy_basedir = os.path.join(basedir, "legacy")
    new_basedir = os.path.join(basedir, "new")

    monkeypatch.setattr(ktp_controller.files, "_LEGACY_DATA_DIR", legacy_basedir)
    monkeypatch.setattr(
        ktp_controller.files, "_EXAM_FILE_DIR", os.path.join(new_basedir, "exam-files")
    )
    monkeypatch.setattr(
        ktp_controller.files,
        "_EXAM_PACKAGE_DIR",
        os.path.join(new_basedir, "exam-packages"),
    )
    monkeypatch.setattr(
        ktp_controller.files,
        "ANSWERS_FILE_DIR",
        os.path.join(new_basedir, "answers-files"),
    )

    return legacy_basedir, new_basedir


def _set_mode(monkeypatch, *, prod_mode, puavo_os):
    monkeypatch.setattr(ktp_controller.files, "is_prod_mode", lambda: prod_mode)
    monkeypatch.setattr(ktp_controller.utils, "is_puavo_os", lambda: puavo_os)


def _make_legacy_entry(legacy_basedir, legacy_subdir_name, dirname, content="data"):
    dirpath = pathlib.Path(legacy_basedir, legacy_subdir_name, dirname)
    dirpath.mkdir(parents=True)
    (dirpath / "file.txt").write_text(content, encoding="utf-8")
    return dirpath


_LEGACY_SUBDIRS_AND_NEW_ATTRS = [
    ("exam-files", "_EXAM_FILE_DIR"),
    ("exam-packages", "_EXAM_PACKAGE_DIR"),
    ("answers-files", "ANSWERS_FILE_DIR"),
]


def test_noop_when_not_in_prod_mode(testdir, monkeypatch):
    legacy_basedir, new_basedir = _setup_dirs(testdir, monkeypatch)
    _set_mode(monkeypatch, prod_mode=False, puavo_os=True)

    _make_legacy_entry(legacy_basedir, "exam-files", "some-uuid")

    ktp_controller.files.migrate_legacy_data_dirs()

    assert _find_all_dirpaths(legacy_basedir) == [
        os.path.join(legacy_basedir, "exam-files"),
        os.path.join(legacy_basedir, "exam-files", "some-uuid"),
    ]
    assert not os.path.exists(new_basedir)


def test_noop_when_not_in_puavo_os(testdir, monkeypatch):
    legacy_basedir, new_basedir = _setup_dirs(testdir, monkeypatch)
    _set_mode(monkeypatch, prod_mode=True, puavo_os=False)

    _make_legacy_entry(legacy_basedir, "exam-files", "some-uuid")

    ktp_controller.files.migrate_legacy_data_dirs()

    assert _find_all_dirpaths(legacy_basedir) == [
        os.path.join(legacy_basedir, "exam-files"),
        os.path.join(legacy_basedir, "exam-files", "some-uuid"),
    ]
    assert not os.path.exists(new_basedir)


def test_noop_when_legacy_dir_does_not_exist(testdir, monkeypatch):
    _setup_dirs(testdir, monkeypatch)
    _set_mode(monkeypatch, prod_mode=True, puavo_os=True)

    # Does not raise, even though nothing exists yet.
    ktp_controller.files.migrate_legacy_data_dirs()


def test_moves_dirs_from_all_three_legacy_locations(testdir, monkeypatch):
    legacy_basedir, _new_basedir = _setup_dirs(testdir, monkeypatch)
    _set_mode(monkeypatch, prod_mode=True, puavo_os=True)

    for legacy_subdir_name, _new_attr in _LEGACY_SUBDIRS_AND_NEW_ATTRS:
        _make_legacy_entry(legacy_basedir, legacy_subdir_name, "some-uuid")

    ktp_controller.files.migrate_legacy_data_dirs()

    for legacy_subdir_name, new_attr in _LEGACY_SUBDIRS_AND_NEW_ATTRS:
        new_basedir_for_type = getattr(ktp_controller.files, new_attr)
        moved_dirpath = pathlib.Path(new_basedir_for_type, "some-uuid")
        assert moved_dirpath.is_dir()
        assert (moved_dirpath / "file.txt").read_text(encoding="utf-8") == "data"

        legacy_dirpath = pathlib.Path(legacy_basedir, legacy_subdir_name, "some-uuid")
        assert not legacy_dirpath.exists()


def test_leaves_legacy_dir_untouched_when_destination_already_exists(
    testdir, monkeypatch
):
    legacy_basedir, _new_basedir = _setup_dirs(testdir, monkeypatch)
    _set_mode(monkeypatch, prod_mode=True, puavo_os=True)

    _make_legacy_entry(
        legacy_basedir, "exam-files", "some-uuid", content="legacy-content"
    )
    existing_dirpath = pathlib.Path(ktp_controller.files._EXAM_FILE_DIR, "some-uuid")
    existing_dirpath.mkdir(parents=True)
    (existing_dirpath / "file.txt").write_text("existing-content", encoding="utf-8")

    ktp_controller.files.migrate_legacy_data_dirs()

    # The already-existing destination directory is left untouched...
    assert (existing_dirpath / "file.txt").read_text(
        encoding="utf-8"
    ) == "existing-content"
    # ...and the legacy directory is left in place rather than being
    # discarded.
    legacy_dirpath = pathlib.Path(legacy_basedir, "exam-files", "some-uuid")
    assert (legacy_dirpath / "file.txt").read_text(encoding="utf-8") == "legacy-content"


def test_ignores_non_directory_entries_in_legacy_dir(testdir, monkeypatch):
    legacy_basedir, _new_basedir = _setup_dirs(testdir, monkeypatch)
    _set_mode(monkeypatch, prod_mode=True, puavo_os=True)

    stray_file_dirpath = pathlib.Path(legacy_basedir, "exam-files")
    stray_file_dirpath.mkdir(parents=True)
    stray_filepath = stray_file_dirpath / "stray-file.txt"
    stray_filepath.write_text("not a dir", encoding="utf-8")

    ktp_controller.files.migrate_legacy_data_dirs()

    assert stray_filepath.exists()
    assert not os.path.exists(ktp_controller.files._EXAM_FILE_DIR)


def test_continues_with_other_dirs_when_one_move_fails(testdir, monkeypatch, caplog):
    legacy_basedir, _new_basedir = _setup_dirs(testdir, monkeypatch)
    _set_mode(monkeypatch, prod_mode=True, puavo_os=True)

    _make_legacy_entry(legacy_basedir, "exam-files", "broken-uuid")
    _make_legacy_entry(legacy_basedir, "exam-files", "ok-uuid")

    real_move = ktp_controller.files.shutil.move

    def _move_raising_for_broken_uuid(src, dst):
        if os.path.basename(src) == "broken-uuid":
            raise OSError("simulated failure")
        return real_move(src, dst)

    monkeypatch.setattr(
        ktp_controller.files.shutil, "move", _move_raising_for_broken_uuid
    )

    with caplog.at_level(logging.ERROR, logger="ktp_controller.files"):
        # Does not raise, despite the simulated failure.
        ktp_controller.files.migrate_legacy_data_dirs()

    assert "broken-uuid" in caplog.text

    # The failing directory is left behind at its legacy location...
    assert pathlib.Path(legacy_basedir, "exam-files", "broken-uuid").exists()
    # ...while the other directory still gets moved.
    assert pathlib.Path(ktp_controller.files._EXAM_FILE_DIR, "ok-uuid").is_dir()
    assert not pathlib.Path(legacy_basedir, "exam-files", "ok-uuid").exists()
