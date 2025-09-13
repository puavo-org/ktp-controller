# Standard library imports
import typing

# Third-party imports

# Internal imports
import ktp_controller.abitti2.words


def make_password(word_list_indices: typing.List[int]) -> str:
    return " ".join([ktp_controller.abitti2.words.WORDS[i] for i in word_list_indices])
