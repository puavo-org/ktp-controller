# Standard library imports
import base64
import contextlib
import datetime
import hashlib
import json
import logging
import os
import sys
import typing
import urllib.parse


__all__ = [
    # Utils:
    "sha256",
    "open_atomic_write",
    "copy_atomic",
    "json_loads_dict",
    "get_url",
    "get_basic_auth",
    "readfirstline",
    "websock_send_json",
]


# Constants:


_LOGGER = logging.getLogger(__file__)
_LOGGER.setLevel(logging.DEBUG)


# Utils:


def sha256(filepath: str, chunk_size_bytes: int = 1024**2) -> str:
    if chunk_size_bytes < 1:
        raise ValueError(
            "invalid chunk_size, must be greater than zero", chunk_size_bytes
        )

    cs = hashlib.sha256()
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(chunk_size_bytes)
            if not chunk:
                break
            cs.update(chunk)

    return cs.hexdigest()


@contextlib.contextmanager
def open_atomic_write(
    dest_filepath: str, exclusive: bool = False, encoding: typing.Optional[str] = None
):
    if exclusive:
        mode = "x"
    else:
        mode = "a"  # "a" does not truncate the file rightaway, rename will do it if all succeeds
    tmpfilemode = "w"

    if encoding is None:
        mode = f"{mode}b"
        tmpfilemode = f"{tmpfilemode}b"

    tmp_dest_filepath = f"{dest_filepath}.ktp_controller_open_atomic_write_tmp"
    success = False
    created_dest_file = False
    created_tmp_file = False
    pre_exists = os.path.exists(dest_filepath)
    try:
        with open(dest_filepath, mode, encoding=encoding) as _:
            created_dest_file = True
            with open(
                tmp_dest_filepath, tmpfilemode, encoding=encoding
            ) as tmp_dest_file:
                created_tmp_file = True
                yield tmp_dest_file
            os.rename(tmp_dest_filepath, dest_filepath)
        success = True
    finally:
        if not success:
            try:
                if not pre_exists and created_dest_file:
                    os.unlink(dest_filepath)
            finally:
                if created_tmp_file:
                    os.unlink(tmp_dest_filepath)


def copy_atomic(src_filepath: str, dest_filepath: str, exclusive: bool = False):
    with open(src_filepath, "rb") as src_file:
        with open_atomic_write(
            dest_filepath, exclusive=exclusive, encoding=None
        ) as dest_file:
            while True:
                data = src_file.read(4096)
                if not data:
                    break
                dest_file.write(data)


def json_loads_dict(string: str) -> typing.Dict[str, typing.Any]:
    try:
        data = json.loads(string)
    except Exception as e:
        raise ValueError("string is not valid JSON") from e

    if not isinstance(data, dict):
        raise ValueError("data is not a dict")

    return data


def get_url(
    host: str,
    path: str,
    *,
    params=None,
    scheme: str = "https",
) -> str:
    r"""Construct valid URL

    >>> get_url('example.invalid', '/what/not')
    'https://example.invalid/what/not'

    >>> get_url('example.invalid', 'another/path/without/leading/slash', scheme='wss')
    'wss://example.invalid/another/path/without/leading/slash'

    >>> get_url('example.invalid:8899', '/what/not', scheme='ftp')
    'ftp://example.invalid:8899/what/not'

    >>> get_url('http://example.invalid:8899', '/what/not')
    Traceback (most recent call last):
    ...
    ValueError: ('invalid host', 'http://example.invalid:8899')

    >>> get_url('example.invalid:8899/', '/what/not/', params={"myid": 7, "color": "black&white right\n"})
    'https://example.invalid:8899/what/not/?myid=7&color=black%26white+right%0A'
    """

    path = path.removeprefix("/")
    host = host.removesuffix("/")

    if host.partition("://")[1]:
        raise ValueError("invalid host", host)

    url = f"{scheme}://{host}/{path}"

    if params is not None:
        url = f"{url}?{urllib.parse.urlencode(params)}"

    return url


def get_basic_auth(username: str, password: str) -> typing.Dict[str, str]:
    auth = base64.b64encode(f"{username}:{password}".encode("ascii")).decode("ascii")
    return {"Authorization": f"Basic {auth}"}


def readfirstline(filepath, encoding=sys.getdefaultencoding()):
    with open(filepath, "r", encoding=encoding) as f:
        return f.readline().rstrip(os.linesep)


async def websock_send_json(websock, data) -> str:
    message = json.dumps(
        data,
        ensure_ascii=True,
        separators=(",", ":"),
    )
    await websock.send(message)

    return message


def utcnow() -> datetime.datetime:
    return datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)


def strfdt(dt: datetime.datetime) -> str:
    return dt.strftime(f"%Y-%m-%dT%H:%M:%S.{dt.microsecond // 1000:0>3}%z")


def utcnow_str() -> str:
    return strfdt(utcnow())


def is_valid_filename(filename: str) -> bool:
    """
    >>> is_valid_filename('foo.json')
    True
    >>> is_valid_filename('/bar/foo.json')
    False
    >>> is_valid_filename('.')
    False
    >>> is_valid_filename('..')
    False
    >>> is_valid_filename('...')
    True
    >>> is_valid_filename('.' * 255)
    True
    >>> is_valid_filename('.' * 256)
    False
    >>> is_valid_filename('foo\\0')
    False
    >>> is_valid_filename('foo\\1')
    True
    >>> is_valid_filename('foo\\nbar')
    True
    >>> is_valid_filename('♆o_$?.! !')
    True
    >>> is_valid_filename('')
    False
    """

    return (
        isinstance(filename, str)
        and len(filename) > 0
        and "\0" not in filename
        and "/" not in filename
        and len(filename.encode("utf-8")) <= 255
        and filename not in (".", "..")
    )


def check_filename(filename: str):
    if not is_valid_filename(filename):
        raise ValueError("invalid filename", filename)


def bytes_stream(filepath: str, chunk_size: int = 4096) -> typing.Iterator[bytes]:
    with open(filepath, "rb") as f:
        while True:
            data = f.read(chunk_size)
            if not data:
                break
            yield data
