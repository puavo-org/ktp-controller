# Standard library imports
import json
import os.path
import typing

# Third-party imports

# Internal imports
import ktp_controller.abitti2.words


_NAKSU2_CONF_DIR_PATH = "~/.local/share/digabi/naksu2"


def make_password(word_list_indices: typing.List[int]) -> str:
    return " ".join([ktp_controller.abitti2.words.WORDS[i] for i in word_list_indices])


def read_naksu2_conf(*, filepath: typing.Optional[str] = None) -> typing.Dict:
    if filepath is None:
        filepath = os.path.join(
            os.path.expanduser(_NAKSU2_CONF_DIR_PATH), "naksu2-config.json"
        )
    with open(filepath, "rb") as f:
        return json.load(f)


def read_password():
    naksu2_conf = read_naksu2_conf()
    return make_password(naksu2_conf["passwordSeed"])


def read_domain():
    with open(
        os.path.join(os.path.expanduser(_NAKSU2_CONF_DIR_PATH), "certs", "domain.txt"),
        "r",
        encoding="utf-8",
    ) as f:
        return f.read().strip()
