import asyncio
import json

import pytest

import ktp_controller.wui.utils


class _FakeBrowserSocket:
    def __init__(self, fail=False):
        self.sent = []
        self.closed_code = None
        self._fail = fail

    async def send_text(self, data):
        if self._fail:
            raise RuntimeError("boom")
        self.sent.append(data)

    async def close(self, code=1000):
        self.closed_code = code


class _FakeWebsocketConnection:
    """Fake async context manager mimicking websockets.connect()'s result."""

    def __init__(self, messages):
        self._messages = messages

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def __aiter__(self):
        return self._generate()

    async def _generate(self):
        for message in self._messages:
            yield message
        raise RuntimeError("fake connection closed")


@pytest.mark.anyio
async def test_registry_notifies_registered_socket():
    registry = ktp_controller.wui.utils.BrowserSocketRegistry()
    websock = _FakeBrowserSocket()
    await registry.register(websock)

    await registry.notify_all()

    assert websock.sent == ["abitti2_stats_changed"]


@pytest.mark.anyio
async def test_registry_unregister_stops_notifications():
    registry = ktp_controller.wui.utils.BrowserSocketRegistry()
    websock = _FakeBrowserSocket()
    await registry.register(websock)
    await registry.unregister(websock)

    await registry.notify_all()

    assert websock.sent == []


@pytest.mark.anyio
async def test_registry_failed_send_does_not_block_other_sockets():
    registry = ktp_controller.wui.utils.BrowserSocketRegistry()
    failing_websock = _FakeBrowserSocket(fail=True)
    ok_websock = _FakeBrowserSocket()
    await registry.register(failing_websock)
    await registry.register(ok_websock)

    await registry.notify_all()

    assert ok_websock.sent == ["abitti2_stats_changed"]
    assert failing_websock.closed_code == 1000


@pytest.mark.anyio
async def test_raw_abitti2_stats_message_listener_notifies_only_on_status_report(
    mocker,
):
    messages = [
        json.dumps({"kind": "abitti2_stats_changed"}),
        json.dumps({"kind": "ping"}),
    ]
    mocker.patch(
        "ktp_controller.wui.utils.websockets.connect",
        return_value=_FakeWebsocketConnection(messages),
    )
    registry = mocker.Mock()
    registry.notify_all = mocker.AsyncMock()

    task = asyncio.create_task(
        ktp_controller.wui.utils.raw_abitti2_stats_message_listener(registry)
    )
    try:
        await asyncio.sleep(0.05)
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    registry.notify_all.assert_awaited_once()


@pytest.mark.anyio
async def test_raw_abitti2_stats_message_listener_notifies_on_abitti2_stats_changed(
    mocker,
):
    messages = [
        json.dumps({"kind": "abitti2_stats_changed"}),
        json.dumps({"kind": "ping"}),
    ]
    mocker.patch(
        "ktp_controller.wui.utils.websockets.connect",
        return_value=_FakeWebsocketConnection(messages),
    )
    registry = mocker.Mock()
    registry.notify_all = mocker.AsyncMock()

    task = asyncio.create_task(
        ktp_controller.wui.utils.raw_abitti2_stats_message_listener(registry)
    )
    try:
        await asyncio.sleep(0.05)
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    registry.notify_all.assert_awaited_once()


@pytest.mark.anyio
async def test_raw_abitti2_stats_message_listener_backs_off_exponentially(mocker):
    delays = []

    async def fake_sleep(delay):
        delays.append(delay)
        if len(delays) >= 3:
            raise asyncio.CancelledError

    mocker.patch("ktp_controller.wui.utils.asyncio.sleep", side_effect=fake_sleep)
    mocker.patch(
        "ktp_controller.wui.utils.websockets.connect",
        side_effect=OSError("connection refused"),
    )
    registry = mocker.Mock()
    registry.notify_all = mocker.AsyncMock()

    with pytest.raises(asyncio.CancelledError):
        await ktp_controller.wui.utils.raw_abitti2_stats_message_listener(registry)

    assert delays == [1, 2, 4]
