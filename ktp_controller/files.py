# Standard library imports
import enum
import os.path

# Third-party imports

# Internal imports

# All exam files will be stored here like so:
# ~/.local/share/ktp-controller/exam-files/FILE_UUID/exam-file_FILE_SHA256.mex
_EXAM_FILE_DIR = os.path.expanduser("~/.local/share/ktp-controller/exam-files")

# All exam packages will be stored here like so:
# ~/.local/share/ktp-controller/exam-packages/EXAM_PACKAGE_UUID/exam-package_COMPOUND_EXAM_FILE_SHA256.zip
_EXAM_PACKAGE_DIR = os.path.expanduser("~/.local/share/ktp-controller/exam-packages")

# All answer files belonging to a known exam package will be stored here like so:
# ~/.local/share/ktp-controller/answer-files/EXAM_PACKAGE_UUID/answer-file_TIMESTAMP.meb
_ANSWERS_FILE_DIR = os.path.expanduser("~/.local/share/ktp-controller/answers-files")

# All orphan answer files, i.e. files downloaded from Abitti2, but
# which could not be reliably linked to any exam package, will be
# stored here like so:
# ~/.local/share/ktp-controller/orphan-answer-files/orphan-answer-file_TIMESTAMP.meb
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
