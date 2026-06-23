# Standard library imports
import logging
import typing

# Third-party imports
import httpx

_LOGGER = logging.getLogger(__name__)

NumberT: typing.TypeAlias = int | float
TimeoutT: typing.TypeAlias = NumberT | None | tuple[NumberT, NumberT]

DEFAULT_TIMEOUT: TimeoutT = (3.1, 60)


def _parse_timeout(timeout: TimeoutT) -> httpx.Timeout | NumberT | None:
    """Convert requests-style timeout tuple (connect, read) to httpx.Timeout."""
    if isinstance(timeout, tuple):
        if len(timeout) != 2:
            raise ValueError("timeout must be a pair of NumberT")
        return httpx.Timeout(timeout[1], connect=timeout[0])
    return timeout


async def get(
    url: str,
    *,
    auth: tuple[str, str] | None = None,
    params: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
    timeout: TimeoutT = DEFAULT_TIMEOUT,
) -> httpx.Response:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            auth=auth,
            timeout=_parse_timeout(timeout),
        )
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as http_status_error:
        if http_status_error.response.text:
            _LOGGER.error(
                "HTTP error %d: %s",
                http_status_error.response.status_code,
                http_status_error.response.text,
            )
        raise
    return response


async def post(
    url: str,
    *,
    auth: tuple[str, str] | None = None,
    params: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
    data: typing.Any | None = None,
    json: typing.Any | None = None,
    content: bytes | None = None,
    files: dict | None = None,
    timeout: TimeoutT = DEFAULT_TIMEOUT,
) -> httpx.Response:

    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            auth=auth,
            params=params,
            headers=headers,
            data=data,
            json=json,
            content=content,
            files=files,
            timeout=_parse_timeout(timeout),
        )

    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as http_status_error:
        if http_status_error.response.text:
            _LOGGER.error(
                "HTTP error %d: %s",
                http_status_error.response.status_code,
                http_status_error.response.text,
            )
        raise
    return response


async def stream_read(
    url: str,
    *,
    auth: tuple[str, str] | None = None,
    params: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
    timeout: TimeoutT = DEFAULT_TIMEOUT,
    chunk_size: int = 4096,
):
    async with httpx.AsyncClient() as client:
        try:
            async with client.stream(
                "GET",
                url,
                auth=auth,
                params=params,
                headers=headers,
                timeout=_parse_timeout(timeout),
            ) as response:
                response.raise_for_status()

                # Iterate over chunks asynchronously
                async for chunk in response.aiter_bytes(chunk_size=chunk_size):
                    yield chunk
        except httpx.HTTPStatusError as http_status_error:
            if http_status_error.response.text:
                _LOGGER.error(
                    "HTTP error %d: %s",
                    http_status_error.response.status_code,
                    http_status_error.response.text,
                )
            raise
