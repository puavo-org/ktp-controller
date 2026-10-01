# Standard library imports
import json
import os.path
import re
import typing

# Third-party imports
# Internal imports
import ktp_controller.abitti2.words

__all__ = [
    "cleanup_rotated_logs",
    "make_password",
    "read_domain",
    "read_naksu2_conf",
    "read_supervisor_passphrase",
]


_NAKSU2_CONF_DIR_PATH = "~/.local/share/digabi/naksu2"


def make_password(word_list_indices: list[int]) -> str:
    return " ".join([ktp_controller.abitti2.words.WORDS[i] for i in word_list_indices])


def read_naksu2_conf(*, filepath: str | None = None) -> dict[str, typing.Any]:
    if filepath is None:
        filepath = os.path.join(
            os.path.expanduser(_NAKSU2_CONF_DIR_PATH), "naksu2-config.json"
        )
    with open(filepath, "rb") as f:
        return typing.cast(dict[str, typing.Any], json.load(f))


def read_supervisor_passphrase() -> str:
    naksu2_conf = read_naksu2_conf()
    return make_password(naksu2_conf["passwordSeed"])


def read_domain() -> str:
    with open(
        os.path.join(os.path.expanduser(_NAKSU2_CONF_DIR_PATH), "certs", "domain.txt"),
        encoding="utf-8",
    ) as f:
        return f.read().strip()


def cleanup_rotated_logs(
    *, deleted_log_filepaths: set[str] | None = None, logs_dirpath: str | None = None
) -> None:
    if logs_dirpath is None:
        logs_dirpath = os.path.join(os.path.expanduser(_NAKSU2_CONF_DIR_PATH), "logs")

    try:
        log_filenames = os.listdir(logs_dirpath)
    except FileNotFoundError:
        return

    exceptions = []

    for log_filename in log_filenames:
        if (
            re.match(
                r"^(.*)\.koe\.abitti\.net(.*)-size\.(log|json)$", log_filename, re.I
            )
            is None
        ):
            # Not a rotated log file
            continue
        try:
            log_filepath = os.path.join(logs_dirpath, log_filename)
            os.unlink(log_filepath)
        except Exception as e:
            exceptions.append(e)
            continue

        if deleted_log_filepaths is not None:
            deleted_log_filepaths.add(log_filepath)

    if exceptions:
        raise ExceptionGroup(
            "Failed to delete some of the rotated Naksu2 log files", exceptions
        )
