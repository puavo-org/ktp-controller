# Standard library imports
import asyncio
import datetime
import enum
import glob
import logging
import os.path
import pathlib
import shutil
import typing

# Third-party imports
# Internal imports
import ktp_controller.schemas

_USER_FRIENDLY_DATA_DIR = os.path.expanduser("~/ktp-jako")

_LOGS_DIR = os.path.expanduser("~/.puavo/puavo-ers/ktp-controller/logs")

# All exam files will be stored here like so:
# ~/.local/share/ktp-controller/exam-files/FILE_UUID/exam-file_FILE_SHA256.mex
_EXAM_FILE_DIR = os.path.expanduser("~/.local/share/ktp-controller/exam-files")

# All exam packages will be stored here like so:
# ~/.local/share/ktp-controller/exam-packages/EXAM_PACKAGE_UUID/exam-package_COMPOUND_EXAM_FILE_SHA256.zip
_EXAM_PACKAGE_DIR = os.path.expanduser("~/.local/share/ktp-controller/exam-packages")

# All answers files belonging to a known exam package will be stored here like so:
# ~/.local/share/ktp-controller/answers-files/EXAM_PACKAGE_UUID/answers-file_TIMESTAMP.meb
ANSWERS_FILE_DIR = os.path.expanduser("~/.local/share/ktp-controller/answers-files")


DUMMY_EXAM_FILE_FILEPATH = os.path.expanduser(
    "~/.local/share/ktp-controller/dummy-exam-file.mex"
)

DUMMY_EXAM_PACKAGE_FILEPATH = os.path.expanduser(
    "~/.local/share/ktp-controller/dummy-exam-package.zip"
)


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


def _find_old_answers_files(
    basedirpath: str | pathlib.Path,
    prefix: str,
    suffix: str,
    *,
    older_than_timedelta: datetime.timedelta = datetime.timedelta(weeks=2),
    logger: logging.Logger | None = None,
) -> typing.Iterator[str]:
    basedirpath = pathlib.Path(basedirpath).expanduser()

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


def find_old_answers_files(
    *,
    older_than_timedelta: datetime.timedelta = datetime.timedelta(weeks=2),
    logger: logging.Logger | None = None,
) -> typing.Iterator[str]:
    """Yields filepaths of all answers files older than the specified
    timedelta (by default, 2 weeks).

    """

    for basedirpath, prefix, suffix in ((ANSWERS_FILE_DIR, "answers-file_", ".meb"),):
        yield from _find_old_answers_files(
            basedirpath,
            prefix,
            suffix,
            older_than_timedelta=older_than_timedelta,
            logger=logger,
        )


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


def _get_archived_exam_package_dirpath(
    archive_filepath: pathlib.Path,
) -> tuple[datetime.datetime, pathlib.Path]:
    with open(archive_filepath, encoding="utf-8") as sentinel_file:
        archived_at_str = sentinel_file.readline().strip()

    archived_at = datetime.datetime.fromisoformat(archived_at_str)

    if archived_at.tzinfo is None:
        raise RuntimeError("naive timestamp")

    archived_exam_package_dirpath = archive_filepath.parent

    if not archived_exam_package_dirpath.is_dir():
        raise NotADirectoryError(archived_exam_package_dirpath)

    return archived_at, archived_exam_package_dirpath


def find_archived_exam_package_dirs(
    *,
    archived_timedelta: datetime.timedelta = datetime.timedelta(days=1),
    exceptions: list[Exception] | None = None,
) -> typing.Iterator[str]:
    """Yields dirpaths of all exam packages archived more than the specified
    timedelta (by default, 1 day) ago.

    If `exceptions` is `None`, exceptions are not handled and
    iteration is stopped when the first exception is
    raised. Otherwise, if `exceptions` is a list, all exceptions
    during the iteration are caught and appended to `exceptions`.

    """
    utcnow: datetime.datetime = ktp_controller.utils.utcnow()
    cutoff_date: datetime.datetime = utcnow - archived_timedelta
    basedirpath: pathlib.Path = pathlib.Path(_EXAM_PACKAGE_DIR)

    if exceptions is not None and not isinstance(exceptions, list):
        raise TypeError("exceptions must be either None or a list")

    for archive_filepath in basedirpath.glob("*/.archived"):
        try:
            archived_at, archived_exam_package_dirpath = (
                _get_archived_exam_package_dirpath(archive_filepath)
            )
        except Exception as e:
            if exceptions is None:
                raise
            exceptions.append(e)
            continue

        if archived_at < cutoff_date:
            yield str(archived_exam_package_dirpath)


def cleanup_archived_exam_packages(
    *,
    archived_timedelta: datetime.timedelta = datetime.timedelta(days=1),
    deleted_exam_package_external_ids: set[str] | None = None,
) -> None:
    exceptions: list[Exception] = []
    for archived_exam_package_dir in find_archived_exam_package_dirs(
        archived_timedelta=archived_timedelta, exceptions=exceptions
    ):
        try:
            shutil.rmtree(archived_exam_package_dir)
        except Exception as e:
            exceptions.append(e)
            continue

        if deleted_exam_package_external_ids is not None:
            deleted_exam_package_external_ids.add(
                os.path.basename(archived_exam_package_dir)
            )

    if exceptions:
        raise ExceptionGroup(
            "failed to cleanup some archived exam packages", exceptions
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

    deleted_exam_package_external_ids: set[str] = set()
    try:
        await asyncio.to_thread(
            cleanup_archived_exam_packages,
            deleted_exam_package_external_ids=deleted_exam_package_external_ids,
        )
    except Exception:
        # cleanup_archived_exam_packages is best-effort; it deletes
        # everything it can and raises exceptions afterwards.
        if logger is not None:
            logger.exception("Failed to cleanup some old exam packages")

    if logger is not None:
        logger.info(
            "Deleted %d archived exam packages", len(deleted_exam_package_external_ids)
        )
