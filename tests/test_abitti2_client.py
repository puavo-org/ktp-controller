import asyncio
import hashlib
import time

import pytest

import ktp_controller.abitti2.client

_POST = "ktp_controller.abitti2.client._post"

_VALID_CODE = {"keyCode": "8223", "confirmationCode": "cx"}


@pytest.mark.anyio
async def test_change_student_access_code_returns_code_from_immediate_response(
    mocker,
):
    post_mock = mocker.patch(
        _POST,
        return_value=mocker.Mock(
            json=mocker.Mock(return_value={"securityCode": _VALID_CODE})
        ),
    )

    result = await ktp_controller.abitti2.client.change_student_access_code()

    assert result == _VALID_CODE
    post_mock.assert_awaited_once_with("/api/single-security-code")


@pytest.mark.anyio
async def test_change_student_access_code_returns_none_when_deferred(mocker):
    mocker.patch(
        _POST,
        return_value=mocker.Mock(json=mocker.Mock(return_value={})),
    )

    result = await ktp_controller.abitti2.client.change_student_access_code()

    assert result is None


@pytest.mark.anyio
@pytest.mark.parametrize(
    "response_body",
    [
        pytest.param({"securityCode": "not a dict"}, id="not-a-dict"),
        pytest.param(
            {"securityCode": {"keyCode": "8223"}}, id="missing-confirmationCode"
        ),
        pytest.param(
            {"securityCode": {"confirmationCode": "cx"}}, id="missing-keyCode"
        ),
        pytest.param(
            {
                "securityCode": {
                    "keyCode": "8223",
                    "confirmationCode": "cx",
                    "extra": "x",
                }
            },
            id="extra-key",
        ),
        pytest.param(
            {"securityCode": {"keyCode": 8223, "confirmationCode": "cx"}},
            id="keyCode-not-str",
        ),
        pytest.param(
            {"securityCode": {"keyCode": "8223", "confirmationCode": 1}},
            id="confirmationCode-not-str",
        ),
    ],
)
async def test_change_student_access_code_returns_none_for_invalid_security_code(
    mocker, response_body
):
    mocker.patch(
        _POST,
        return_value=mocker.Mock(json=mocker.Mock(return_value=response_body)),
    )

    result = await ktp_controller.abitti2.client.change_student_access_code()

    assert result is None


def _mock_naksu2(mocker):
    mocker.patch(
        "ktp_controller.abitti2.naksu2.read_domain",
        return_value="abitti2.example.invalid",
    )
    mocker.patch(
        "ktp_controller.abitti2.naksu2.read_supervisor_passphrase",
        return_value="secret",
    )


@pytest.mark.anyio
async def test_download_answers_file_writes_content_and_returns_matching_sha256(
    mocker, tmp_path
):
    _mock_naksu2(mocker)
    chunks = [b"abc", b"def", b"ghi"]

    async def _fake_stream_read(url, **kwargs):
        for chunk in chunks:
            yield chunk

    mocker.patch("ktp_controller.httpx2.stream_read", new=_fake_stream_read)

    dest_filepath = str(tmp_path / "answers.meb")

    sha256sum = await ktp_controller.abitti2.client.download_answers_file(dest_filepath)

    with open(dest_filepath, "rb") as dest_file:
        assert dest_file.read() == b"".join(chunks)
    assert sha256sum == hashlib.sha256(b"".join(chunks)).hexdigest()


@pytest.mark.anyio
async def test_download_answers_file_does_not_block_event_loop_while_writing(
    mocker, tmp_path
):
    # Regression test: writing each chunk to disk and hashing it must
    # happen in a worker thread, not inline on the event loop, so that a
    # large (or slowly-written-to-disk) answers file can't starve
    # unrelated tasks sharing the same event loop (e.g. the websocket
    # keepalive to the API).
    _mock_naksu2(mocker)
    chunk_count = 10
    chunk_sleep_sec = 0.05

    async def _fake_stream_read(url, **kwargs):
        for _ in range(chunk_count):
            yield b"x"

    mocker.patch("ktp_controller.httpx2.stream_read", new=_fake_stream_read)
    mocker.patch(
        "ktp_controller.abitti2.client._write_and_hash_chunk",
        side_effect=lambda dest_file, sha256sum, chunk: time.sleep(chunk_sleep_sec),
    )

    tick_count = 0

    async def _count_event_loop_ticks():
        nonlocal tick_count
        while True:
            await asyncio.sleep(0.01)
            tick_count += 1

    ticker = asyncio.create_task(_count_event_loop_ticks())
    try:
        await ktp_controller.abitti2.client.download_answers_file(
            str(tmp_path / "answers.meb")
        )
    finally:
        ticker.cancel()

    # chunk_count * chunk_sleep_sec = 500ms of blocking "disk I/O" in
    # total. If that ran inline on the event loop, this concurrently
    # running ticker (woken every 10ms) would get almost no chance to
    # run during that window. Offloaded to a worker thread, the loop
    # stays free, so it should tick dozens of times.
    assert tick_count > 20
