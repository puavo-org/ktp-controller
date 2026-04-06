# Standard library imports
import datetime
import enum
import logging
import os.path
import pathlib

# Third-party imports

# Internal imports
import ktp_controller.schemas

# All exam files will be stored here like so:
# ~/.local/share/ktp-controller/exam-files/FILE_UUID/exam-file_FILE_SHA256.mex
_EXAM_FILE_DIR = os.path.expanduser("~/.local/share/ktp-controller/exam-files")

# All exam packages will be stored here like so:
# ~/.local/share/ktp-controller/exam-packages/EXAM_PACKAGE_UUID/exam-package_COMPOUND_EXAM_FILE_SHA256.zip
_EXAM_PACKAGE_DIR = os.path.expanduser("~/.local/share/ktp-controller/exam-packages")

# All answers files belonging to a known exam package will be stored here like so:
# ~/.local/share/ktp-controller/answers-files/EXAM_PACKAGE_UUID/answers-file_TIMESTAMP.meb
_ANSWERS_FILE_DIR = os.path.expanduser("~/.local/share/ktp-controller/answers-files")

# All orphan answers files, i.e. files downloaded from Abitti2, but
# which could not be reliably linked to any exam package, will be
# stored here like so:
# ~/.local/share/ktp-controller/orphan-answers-files/unknown/orphan-answers-file_TIMESTAMP.meb
_ORPHAN_ANSWERS_FILE_DIR = os.path.expanduser(
    "~/.local/share/ktp-controller/orphan-answers-files"
)

DUMMY_EXAM_FILE_FILEPATH = os.path.expanduser(
    "~/.local/share/ktp-controller/dummy-exam-file.mex"
)

DUMMY_EXAM_PACKAGE_FILEPATH = os.path.expanduser(
    "~/.local/share/ktp-controller/dummy-exam-package.zip"
)


class LocalFilepathType(str, enum.Enum):
    ANSWERS_FILE = "answers-file"
    EXAM_FILE = "exam-file"
    EXAM_PACKAGE = "exam-package"
    ORPHAN_ANSWERS_FILE = "orphan-answers-file"

    def __str__(self) -> str:
        return self.value


def get_local_dirpath(local_filepath_type: LocalFilepathType, dirname: str) -> str:
    LocalFilepathType(local_filepath_type)
    if local_filepath_type == LocalFilepathType.EXAM_FILE:
        basedir = _EXAM_FILE_DIR
    elif local_filepath_type == LocalFilepathType.EXAM_PACKAGE:
        basedir = _EXAM_PACKAGE_DIR
    elif local_filepath_type == LocalFilepathType.ANSWERS_FILE:
        basedir = _ANSWERS_FILE_DIR
    elif local_filepath_type == LocalFilepathType.ORPHAN_ANSWERS_FILE:
        basedir = _ORPHAN_ANSWERS_FILE_DIR
    else:
        raise ValueError("invalid local_filepath_type")

    return os.path.join(basedir, dirname)


def get_local_filepath(
    local_filepath_type: LocalFilepathType, dirname: str, filename_suffix: str
) -> str:
    LocalFilepathType(local_filepath_type)
    if local_filepath_type == LocalFilepathType.EXAM_FILE:
        basedir = _EXAM_FILE_DIR
        ext = ".mex"
    elif local_filepath_type == LocalFilepathType.EXAM_PACKAGE:
        basedir = _EXAM_PACKAGE_DIR
        ext = ".zip"
    elif local_filepath_type == LocalFilepathType.ANSWERS_FILE:
        basedir = _ANSWERS_FILE_DIR
        ext = ".meb"
    elif local_filepath_type == LocalFilepathType.ORPHAN_ANSWERS_FILE:
        basedir = _ORPHAN_ANSWERS_FILE_DIR
        ext = ".meb"
    else:
        raise ValueError("invalid local_filepath_type")

    dirpath = os.path.join(basedir, dirname)

    try:
        os.makedirs(dirpath)
    except FileExistsError:
        pass

    return os.path.join(dirpath, f"{local_filepath_type}_{filename_suffix}{ext}")


def get_stats() -> ktp_controller.schemas.FileStats:
    data = {}

    for key, dirpath in zip(
        ["exams", "exam_packages", "answers"],
        [_EXAM_FILE_DIR, _EXAM_PACKAGE_DIR, _ANSWERS_FILE_DIR],
    ):
        items = data.setdefault(key, [])
        for path, dirnames, filenames in os.walk(dirpath):
            for filename in filenames:
                filepath = os.path.join(path, filename)
                items.append(
                    {
                        "path": filepath,
                        "modified_at": datetime.datetime.fromtimestamp(
                            os.path.getmtime(filepath), datetime.timezone.utc
                        ),
                        "size": os.path.getsize(filepath),
                    }
                )

    return ktp_controller.schemas.FileStats.model_validate(data)


def _find_old_answers_files(
    basedirpath: str | pathlib.Path,
    prefix: str,
    suffix: str,
    *,
    older_than_timedelta: datetime.timedelta = datetime.timedelta(weeks=2),
    logger: logging.Logger | None = None,
):
    basedirpath = pathlib.Path(basedirpath).expanduser()

    if not basedirpath.exists():
        return

    now = datetime.datetime.now(datetime.timezone.utc)
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
            logger is None or logger.warning(
                "Ignoring invalid answers file '%s': invalid timestamp: %r",
                filepath,
                timestamp_str,
            )
            continue

        if timestamp.tzinfo is None:
            logger is None or logger.warning(
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
):
    """Yields filepaths of all answers files older than the specified
    timedelta (by default, 2 weeks).

    """

    for basedirpath, prefix, suffix in (
        (_ANSWERS_FILE_DIR, "answers-file_", ".meb"),
        (_ORPHAN_ANSWERS_FILE_DIR, "orphan-answers-file_", ".meb"),
    ):
        for p in _find_old_answers_files(
            basedirpath,
            prefix,
            suffix,
            older_than_timedelta=older_than_timedelta,
            logger=logger,
        ):
            yield p


def find_empty_dirs_bottom_up(basedirpath: str | pathlib.Path):
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
) -> [str]:
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
) -> [str]:
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

    try:
        rmdir_recursively_bottom_up(_ANSWERS_FILE_DIR)
        rmdir_recursively_bottom_up(_ORPHAN_ANSWERS_FILE_DIR)
    except Exception:
        # Not fatal.
        logger is None or logger.error("failed to cleanup empty dirs")

    return deleted_answers_files
