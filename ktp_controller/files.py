# Standard library imports
import asyncio
import datetime
import enum
import glob
import logging
import os.path
import pathlib
import shutil
import time
import typing

# Third-party imports
# Internal imports
import ktp_controller.schemas

_USER_FRIENDLY_DATA_DIR = os.path.expanduser("~/ktp-jako")

_LOGS_DIR = os.path.expanduser("~/.puavo/puavo-ers/ktp-controller/logs")

_BASEDIRPATH = os.path.expanduser("~/.local/share/ktp-controller")

# All exam files will be stored here like so:
# ~/.local/share/ktp-controller/exam-files/FILE_UUID/exam-file_FILE_SHA256.mex
_EXAM_FILE_DIR = os.path.join(_BASEDIRPATH, "exam-files")

# All exam packages will be stored here like so:
# ~/.local/share/ktp-controller/exam-packages/EXAM_PACKAGE_UUID/exam-package_COMPOUND_EXAM_FILE_SHA256.zip
_EXAM_PACKAGE_DIR = os.path.join(_BASEDIRPATH, "exam-packages")

# All answers files belonging to a known exam package will be stored here like so:
# ~/.local/share/ktp-controller/answers-files/EXAM_PACKAGE_UUID/answers-file_TIMESTAMP.meb
ANSWERS_FILE_DIR = os.path.join(_BASEDIRPATH, "answers-files")


DUMMY_EXAM_FILE_FILEPATH = os.path.join(_BASEDIRPATH, "dummy-exam-file.mex")

DUMMY_EXAM_PACKAGE_FILEPATH = os.path.join(_BASEDIRPATH, "dummy-exam-package.zip")


def create_user_friendly_data_dir() -> None:
    try:
        os.makedirs(_USER_FRIENDLY_DATA_DIR)
    except FileExistsError:
        pass
    for symlink_target in (
        _EXAM_FILE_DIR,
        _EXAM_PACKAGE_DIR,
        ANSWERS_FILE_DIR,
        _LOGS_DIR,
    ):
        symlink_filename = os.path.basename(symlink_target)
        try:
            os.symlink(
                symlink_target,
                os.path.join(_USER_FRIENDLY_DATA_DIR, symlink_filename),
            )
        except FileExistsError:
            continue


class LocalFilepathType(enum.StrEnum):
    ANSWERS_FILE = "answers-file"
    EXAM_FILE = "exam-file"
    EXAM_PACKAGE = "exam-package"

    def __str__(self) -> str:
        return self.value


def _get_local_filepath_basedir_and_ext(
    local_filepath_type: LocalFilepathType,
) -> tuple[str, str]:
    LocalFilepathType(local_filepath_type)

    if local_filepath_type == LocalFilepathType.EXAM_FILE:
        basedir = _EXAM_FILE_DIR
        ext = ".mex"
    elif local_filepath_type == LocalFilepathType.EXAM_PACKAGE:
        basedir = _EXAM_PACKAGE_DIR
        ext = ".zip"
    elif local_filepath_type == LocalFilepathType.ANSWERS_FILE:
        basedir = ANSWERS_FILE_DIR
        ext = ".meb"
    else:
        raise ValueError("invalid local_filepath_type")

    return basedir, ext


def get_local_dirpath(local_filepath_type: LocalFilepathType, dirname: str) -> str:
    basedir, _ = _get_local_filepath_basedir_and_ext(local_filepath_type)

    dirpath = os.path.join(basedir, dirname)

    try:
        os.makedirs(dirpath)
    except FileExistsError:
        pass

    return dirpath


def glob_local_filepath(
    local_filepath_type: LocalFilepathType, dirname: str, filestem_pattern: str
) -> list[str]:
    if os.path.sep in filestem_pattern:
        raise ValueError("invalid pattern")

    basedir, ext = _get_local_filepath_basedir_and_ext(local_filepath_type)

    dirpath = os.path.join(basedir, dirname)

    return [
        os.path.join(dirpath, f)
        for f in glob.glob(f"{filestem_pattern}{ext}", root_dir=dirpath)
    ]


def get_local_filepath(
    local_filepath_type: LocalFilepathType, dirname: str, filename_suffix: str
) -> str:
    basedir, ext = _get_local_filepath_basedir_and_ext(local_filepath_type)

    dirpath = os.path.join(basedir, dirname)

    try:
        os.makedirs(dirpath)
    except FileExistsError:
        pass

    return os.path.join(dirpath, f"{local_filepath_type}_{filename_suffix}{ext}")


def get_cached_files(
    *, include_archived: bool = False
) -> dict[str, list[dict[str, typing.Any]]]:
    """
    If include_archived is True, archived files and/or directories are included.
    """

    data: dict[str, typing.Any] = {}

    for key, dirpath in zip(
        ["exams", "exam_packages", "answers"],
        [_EXAM_FILE_DIR, _EXAM_PACKAGE_DIR, ANSWERS_FILE_DIR],
        strict=False,
    ):
        items = data.setdefault(key, [])
        for path, dirnames, filenames in os.walk(dirpath):
            if not include_archived and ".archived" in filenames:
                dirnames.clear()
                filenames.clear()
                continue
            for filename in filenames:
                filepath = os.path.join(path, filename)
                if not include_archived and os.path.exists(f"{filepath}.archived"):
                    continue
                items.append(
                    {
                        "path": filepath,
                        "modified_at": datetime.datetime.fromtimestamp(
                            os.path.getmtime(filepath), datetime.UTC
                        ),
                        "size": os.path.getsize(filepath),
                    }
                )

    return data


def find_old_answers_files(
    older_than_timedelta: datetime.timedelta = datetime.timedelta(weeks=2),
    logger: logging.Logger | None = None,
) -> typing.Iterator[str]:
    """Yields filepaths of all answers files older than the specified
    timedelta (by default, 2 weeks).

    """

    basedirpath = pathlib.Path(ANSWERS_FILE_DIR).expanduser()
    prefix = "answers-file_"
    suffix = ".meb"

    if not basedirpath.exists():
        return

    now = datetime.datetime.now(datetime.UTC)
    cutoff_date = now - older_than_timedelta

    # Use glob to match exactly one directory deep (the UUID) and the specific filename pattern
    for filepath in basedirpath.glob(f"*/{prefix}*{suffix}"):
        filename = filepath.name

        if not filename.startswith(prefix) or not filename.endswith(suffix):
            # Unknown file.
            continue

        timestamp_str = filename[len(prefix) : -len(suffix)]
        if timestamp_str.endswith("_final"):
            timestamp_str = timestamp_str[0 : -len("_final")]

        try:
            timestamp = datetime.datetime.fromisoformat(timestamp_str)
        except ValueError:
            if logger is not None:
                logger.warning(
                    "Ignoring invalid answers file '%s': invalid timestamp: %r",
                    filepath,
                    timestamp_str,
                )
            continue

        if timestamp.tzinfo is None:
            if logger is not None:
                logger.warning(
                    "Igoring invalid answers file '%s': timestamp lacks timezone information",
                    filepath,
                )
            continue

        if timestamp < cutoff_date:
            yield str(filepath)


def find_empty_dirs_bottom_up(
    basedirpath: str | pathlib.Path,
) -> typing.Iterator[str]:
    """Yields empty directories bottom-up. Because it yields lazily,
    parent directories will correctly register as empty if their
    children were deleted by the caller between iterations.

    """
    basedirpath = pathlib.Path(basedirpath).expanduser()

    if not basedirpath.exists():
        return

    if not basedirpath.is_dir():
        return

    # Find all directories and sort them by depth, deepest first (bottom-up)
    # len(p.parts) counts how many folders deep a path is.
    dirpaths = sorted(
        (d for d in basedirpath.rglob("*") if d.is_dir()),
        key=lambda p: len(p.parts),
        reverse=True,
    )

    for dirpath in dirpaths:
        if dirpath.is_dir():
            try:
                # iterdir() creates an iterator of the directory's contents.
                # calling next() tries to fetch just the very first item.
                next(dirpath.iterdir())
            except StopIteration:
                # If StopIteration is immediately raised, there is no first item.
                # This means the directory is completely empty.
                yield str(dirpath)
            except (PermissionError, FileNotFoundError):
                # FileNotFoundError catches cases where another process
                # (or the OS) deleted the folder after our initial rglob scan.
                continue


def rmdir_recursively_bottom_up(
    basedirpath: str | pathlib.Path,
) -> list[str]:
    """Recursively finds and deletes empty directories, working
    bottom-up so that newly emptied parent directories are also
    deleted.

    """

    deleted_empty_dirpaths = []
    exceptions = []

    for empty_dirpath in find_empty_dirs_bottom_up(basedirpath):
        try:
            # Path.rmdir() is inherently safe: it ONLY deletes strictly empty directories.
            # If a directory contains files, rmdir() raises an OSError.
            pathlib.Path(empty_dirpath).rmdir()
        except Exception as e:
            exceptions.append(e)
            continue
        deleted_empty_dirpaths.append(empty_dirpath)

    if exceptions:
        raise ExceptionGroup("failed to remove empty dirs", exceptions)

    return deleted_empty_dirpaths


def cleanup_old_answers_files(
    *,
    older_than_timedelta: datetime.timedelta = datetime.timedelta(weeks=2),
    logger: logging.Logger | None = None,
) -> list[str]:
    deleted_answers_files = []
    exceptions = []

    for answers_file_filepath in find_old_answers_files(
        older_than_timedelta=older_than_timedelta, logger=logger
    ):
        try:
            os.unlink(answers_file_filepath)
        except Exception as e:
            exceptions.append(e)
        else:
            deleted_answers_files.append(answers_file_filepath)
            sentinel_file_filepath = f"{answers_file_filepath}.archived"
            if os.path.exists(sentinel_file_filepath):
                try:
                    os.unlink(sentinel_file_filepath)
                except Exception as e:
                    exceptions.append(e)

    if exceptions:
        raise ExceptionGroup("failed to cleanup old answers files", exceptions)

    return deleted_answers_files


def _get_archived_dirpath(
    archive_filepath: str | pathlib.Path,
) -> tuple[datetime.datetime, pathlib.Path]:
    archive_filepath = pathlib.Path(archive_filepath)

    with open(archive_filepath, encoding="utf-8") as sentinel_file:
        archived_at_str = sentinel_file.readline().strip()

    archived_at = datetime.datetime.fromisoformat(archived_at_str)

    if archived_at.tzinfo is None:
        raise RuntimeError("naive timestamp")

    archived_dirpath = archive_filepath.parent

    if not archived_dirpath.is_dir():
        raise NotADirectoryError(archived_dirpath)

    return archived_at, archived_dirpath


def find_archived_dirs(
    *,
    basedirpath: str | pathlib.Path,
    archived_timedelta: datetime.timedelta = datetime.timedelta(days=1),
    exceptions: list[Exception] | None = None,
) -> typing.Iterator[str]:
    """Yields dirpaths of all directories archived more than the specified
    timedelta (by default, 1 day) ago.

    If `exceptions` is `None`, exceptions are not handled and
    iteration is stopped when the first exception is
    raised. Otherwise, if `exceptions` is a list, all exceptions
    during the iteration are caught and appended to `exceptions`.

    """
    utcnow: datetime.datetime = ktp_controller.utils.utcnow()
    cutoff_date: datetime.datetime = utcnow - archived_timedelta

    basedirpath = pathlib.Path(basedirpath).expanduser().resolve()

    for archive_filepath in glob.glob(
        "**/.archived", root_dir=basedirpath, recursive=True, include_hidden=True
    ):
        try:
            archived_at, archived_dirpath = _get_archived_dirpath(
                basedirpath.joinpath(archive_filepath)
            )
        except Exception as e:
            if exceptions is None:
                raise
            exceptions.append(e)
            continue

        if archived_at < cutoff_date:
            yield str(archived_dirpath)


def cleanup_archived_dirs(
    *,
    basedirpath: pathlib.Path | str,
    archived_timedelta: datetime.timedelta = datetime.timedelta(days=1),
    deleted_dirpaths: set[str] | None = None,
) -> None:
    exceptions: list[Exception] = []
    for archived_dir in find_archived_dirs(
        basedirpath=basedirpath,
        archived_timedelta=archived_timedelta,
        exceptions=exceptions,
    ):
        try:
            shutil.rmtree(archived_dir)
        except Exception as e:
            exceptions.append(e)
            continue

        if deleted_dirpaths is not None:
            deleted_dirpaths.add(os.path.basename(archived_dir))

    if exceptions:
        raise ExceptionGroup("failed to cleanup some archived directories", exceptions)


def cleanup_old_files(
    *,
    basedirpath: str | pathlib.Path,
    mtime_older_than_days: int,
    select_func: typing.Callable[[pathlib.Path], bool] = lambda _fp: False,
    deleted_filepaths: set[str] | None = None,
) -> int:
    """Delete files older than given days.

    Deletions are carried out as best-effort: the procedure tries to
    delete all files matching the criteria and raises exception group
    afterwards. I.e. failure to delete one file does not block
    deleting other files.

    Filepaths for which select_func returns False are ignored. The
    default select_func returns True for all filepaths.

    If deleted_filepaths is given, all deleted file paths are added to it.

    Return the number of deleted files.

    """

    if mtime_older_than_days < 0:
        raise ValueError("older_than_days cannot be negative")

    seconds_since_epoch_now = time.time()
    old_mtime = seconds_since_epoch_now - (mtime_older_than_days * 24 * 60 * 60)

    try:
        basedirpath = pathlib.Path(basedirpath).expanduser().resolve(strict=True)
    except FileNotFoundError:
        return 0

    delete_count = 0
    exceptions = []
    try_count = 0

    for dirpath, _, filenames in os.walk(basedirpath):
        for filename in filenames:
            filepath = pathlib.Path(dirpath).joinpath(filename)
            if not select_func(filepath):
                continue

            if filepath.stat().st_mtime >= old_mtime:
                continue

            try_count += 1

            try:
                filepath.unlink()
            except Exception as e:
                exceptions.append(e)
                continue

            delete_count += 1

            if deleted_filepaths is not None:
                deleted_filepaths.add(str(filepath))

        if exceptions:
            raise ExceptionGroup(
                f"failed to delete {len(exceptions)}/{try_count} old files",
                exceptions,
            )

    return delete_count


def cleanup_exam_files(
    *,
    mtime_older_than_days: int = 30,
    deleted_filepaths: set[str] | None = None,
) -> int:
    """Delete exam files older than given days.

    Deletions are carried out as best-effort: the procedure tries to
    delete all files matching the criteria and raises exception group
    afterwards. I.e. failure to delete one file does not block
    deleting other files.

    If deleted_filepaths is given, all deleted exam file paths are added to it.

    Return the number of deleted exam files.

    """
    return cleanup_old_files(
        basedirpath=_EXAM_FILE_DIR,
        mtime_older_than_days=mtime_older_than_days,
        deleted_filepaths=deleted_filepaths,
        select_func=lambda fp: str(fp).endswith(".mex"),
    )


def cleanup_log_files(
    *,
    mtime_older_than_days: int = 14,
    deleted_filepaths: set[str] | None = None,
) -> int:
    """Delete log files older than given days.

    Deletions are carried out as best-effort: the procedure tries to
    delete all files matching the criteria and raises exception group
    afterwards. I.e. failure to delete one file does not block
    deleting other files.

    If deleted_filepaths is given, all deleted log file paths are added to it.

    Return the number of deleted log files.

    """
    return cleanup_old_files(
        basedirpath=_LOGS_DIR,
        mtime_older_than_days=mtime_older_than_days,
        deleted_filepaths=deleted_filepaths,
        select_func=lambda fp: str(fp).endswith(".log"),
    )


async def cleanup_files(logger: logging.Logger | None = None) -> None:
    try:
        deleted_answers_files = await asyncio.to_thread(cleanup_old_answers_files)
    except Exception:
        # cleanup_old_answers_files is best-effort; it deletes
        # everything it can and raises exceptions afterwards.
        if logger is not None:
            logger.exception("Failed to cleanup some old answers files")
    else:
        if logger is not None:
            logger.info("Deleted %d old answers files", len(deleted_answers_files))

    deleted_log_filepaths: set[str] = set()
    try:
        await asyncio.to_thread(
            cleanup_log_files,
            deleted_filepaths=deleted_log_filepaths,
        )
    except Exception:
        # cleanup_log_files is best-effort; it deletes
        # everything it can and raises exceptions afterwards.
        if logger is not None:
            logger.exception("Failed to cleanup some old log files")

    if logger is not None:
        logger.info("Deleted %d old log files", len(deleted_log_filepaths))

    deleted_exam_filepaths: set[str] = set()
    try:
        await asyncio.to_thread(
            cleanup_exam_files,
            deleted_filepaths=deleted_exam_filepaths,
        )
    except Exception:
        # cleanup_exam_files is best-effort; it deletes
        # everything it can and raises exceptions afterwards.
        if logger is not None:
            logger.exception("Failed to cleanup some old exam files")

    if logger is not None:
        logger.info("Deleted %d old exam files", len(deleted_exam_filepaths))

    deleted_archived_dirpaths: set[str] = set()
    try:
        await asyncio.to_thread(
            cleanup_archived_dirs,
            basedirpath=_BASEDIRPATH,
            deleted_dirpaths=deleted_archived_dirpaths,
        )
    except Exception:
        # cleanup_archived_dirs is best-effort; it deletes
        # everything it can and raises exceptions afterwards.
        if logger is not None:
            logger.exception("Failed to cleanup some archived directories")

    if logger is not None:
        logger.info("Deleted %d archived directories", len(deleted_archived_dirpaths))

    try:
        deleted_empty_dirs = await asyncio.to_thread(
            rmdir_recursively_bottom_up,
            basedirpath=_BASEDIRPATH,
        )
    except Exception:
        # rmdir_recursively_bottom_up is best-effort; it deletes
        # everything it can and raises exceptions afterwards.
        if logger is not None:
            logger.exception("Failed to delete some empty directories")

    if logger is not None:
        logger.info("Deleted %d empty directories", len(deleted_empty_dirs))
