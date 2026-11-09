import asyncio
import contextlib
import datetime

import pytest

import ktp_controller.agent.tasks.base as task_base
import ktp_controller.agent.tasks.student_access_code as student_access_code

_UTCNOW = "ktp_controller.utils.utcnow"
_CHANGE = "ktp_controller.abitti2.client.change_student_access_code"

_T0 = datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC)

_OLD_CODE = {"keyCode": "AAA", "confirmationCode": "111"}
_NEW_CODE = {"keyCode": "BBB", "confirmationCode": "222"}


@contextlib.asynccontextmanager
async def _running(task: student_access_code.StudentAccessCodeTask):
    consumer = asyncio.create_task(task.run_consumer())
    try:
        yield
    finally:
        # task_guard() only lets a cancellation through as CancelledError
        # (instead of raising UnexpectedCancel) while a shutdown is in
        # progress, so simulate one for this orderly teardown.
        task_base.SHUTDOWN_EVENT.set()
        try:
            consumer.cancel()
            with pytest.raises(asyncio.CancelledError):
                await consumer
        finally:
            task_base.SHUTDOWN_EVENT.clear()


# StudentAccessCodeTask.request_change / run_consumer


@pytest.mark.anyio
async def test_request_change_calls_abitti2_and_resolves_true(mocker):
    change_mock = mocker.patch(_CHANGE, return_value=None)
    mocker.patch(_UTCNOW, return_value=_T0)

    task = student_access_code.StudentAccessCodeTask()
    async with _running(task):
        assert await task.request_change() is True

    change_mock.assert_awaited_once()


@pytest.mark.anyio
async def test_concurrent_requests_coalesce_into_one_batch(mocker):
    call_count = 0
    started = asyncio.Event()
    gate = asyncio.Event()

    async def fake_change_student_access_code():
        nonlocal call_count
        call_count += 1
        started.set()
        await gate.wait()

    mocker.patch(_CHANGE, side_effect=fake_change_student_access_code)
    # Timestamps far enough apart that the cooldown never interferes;
    # this test is only about coalescing, not the cooldown.
    mocker.patch(_UTCNOW, side_effect=[_T0, _T0 + datetime.timedelta(seconds=120)])

    task = student_access_code.StudentAccessCodeTask()
    async with _running(task):
        # This first request starts the one in-flight run.
        first = asyncio.create_task(task.request_change())
        await started.wait()
        assert call_count == 1

        # Two more requests arrive while the first run is still in
        # flight. They must coalesce into at most one more run, not two.
        second = asyncio.create_task(task.request_change())
        third = asyncio.create_task(task.request_change())
        await asyncio.sleep(0)

        gate.set()
        results = await asyncio.gather(first, second, third)

    assert call_count == 2
    assert results == [True, True, True]


@pytest.mark.anyio
async def test_batch_within_cooldown_resolves_false_without_calling_abitti2(mocker):
    change_mock = mocker.patch(_CHANGE, return_value=None)
    mocker.patch(_UTCNOW, side_effect=[_T0, _T0 + datetime.timedelta(seconds=10)])

    task = student_access_code.StudentAccessCodeTask()
    async with _running(task):
        assert await task.request_change() is True
        assert await task.request_change() is False

    change_mock.assert_awaited_once()


@pytest.mark.anyio
async def test_batch_after_cooldown_calls_abitti2_again(mocker):
    change_mock = mocker.patch(_CHANGE, return_value=None)
    mocker.patch(_UTCNOW, side_effect=[_T0, _T0 + datetime.timedelta(seconds=21)])

    task = student_access_code.StudentAccessCodeTask()
    async with _running(task):
        assert await task.request_change() is True
        assert await task.request_change() is True

    assert change_mock.await_count == 2


# StudentAccessCodeTask.ensure_code_changed


@pytest.mark.anyio
async def test_ensure_code_changed_waits_until_code_differs(mocker):
    # Abitti2 does not report the new code in the API response here
    # (return_value=None), so this exercises the websocket-fallback
    # path: last_received_security_code must change before this
    # resolves True.
    mocker.patch(_CHANGE, return_value=None)
    mocker.patch(_UTCNOW, return_value=_T0)

    task = student_access_code.StudentAccessCodeTask()
    async with _running(task):
        assert (
            await task.ensure_code_changed(
                auto_control_enabled=True, last_received_security_code=_OLD_CODE
            )
            is False
        )
        assert (
            await task.ensure_code_changed(
                auto_control_enabled=True, last_received_security_code=_OLD_CODE
            )
            is False
        )
        assert (
            await task.ensure_code_changed(
                auto_control_enabled=True, last_received_security_code=_NEW_CODE
            )
            is True
        )


@pytest.mark.anyio
async def test_ensure_code_changed_detects_change_immediately_via_api_response(
    mocker,
):
    # Abitti2 reports the new code directly in the API response here,
    # so a single call must resolve True without needing a subsequent
    # websocket-driven last_received_security_code update.
    mocker.patch(_CHANGE, return_value=_NEW_CODE)
    mocker.patch(_UTCNOW, return_value=_T0)

    task = student_access_code.StudentAccessCodeTask()
    async with _running(task):
        assert (
            await task.ensure_code_changed(
                auto_control_enabled=True, last_received_security_code=_OLD_CODE
            )
            is True
        )


@pytest.mark.anyio
async def test_ensure_code_changed_does_not_reuse_stale_api_reported_code(mocker):
    # Regression test: Abitti2 can be reset back to a default code
    # between exam packages (e.g. via ktp_controller.abitti2.client.reset())
    # without the task being told. If that reset code is then observed
    # again via websocket while still within the request cooldown, the
    # code Abitti2 reported immediately for a *previous*, now-irrelevant
    # change must not be mistaken for a fresh change away from it.
    change_mock = mocker.patch(_CHANGE, return_value=_NEW_CODE)
    mocker.patch(_UTCNOW, return_value=_T0)

    task = student_access_code.StudentAccessCodeTask()
    async with _running(task):
        assert (
            await task.ensure_code_changed(
                auto_control_enabled=True, last_received_security_code=_OLD_CODE
            )
            is True
        )

        # Abitti2 is reset externally back to _OLD_CODE and that is
        # observed via websocket again, still within the cooldown
        # window from the change above.
        assert (
            await task.ensure_code_changed(
                auto_control_enabled=True, last_received_security_code=_OLD_CODE
            )
            is False
        )

    assert change_mock.await_count == 1


@pytest.mark.anyio
async def test_ensure_code_changed_short_circuits_when_auto_control_disabled():
    task = student_access_code.StudentAccessCodeTask()
    assert (
        await task.ensure_code_changed(
            auto_control_enabled=False, last_received_security_code=None
        )
        is True
    )


@pytest.mark.anyio
async def test_ensure_code_changed_short_circuits_when_automatic_change_disabled(
    mocker,
):
    mocker.patch.object(
        student_access_code.SETTINGS,
        "abitti2_change_student_access_code_automatically",
        False,
    )
    task = student_access_code.StudentAccessCodeTask()
    assert (
        await task.ensure_code_changed(
            auto_control_enabled=True, last_received_security_code=None
        )
        is True
    )


@pytest.mark.anyio
async def test_ensure_code_changed_returns_false_until_security_code_is_known():
    task = student_access_code.StudentAccessCodeTask()
    assert (
        await task.ensure_code_changed(
            auto_control_enabled=True, last_received_security_code=None
        )
        is False
    )


# StudentAccessCodeTask.reset


@pytest.mark.anyio
async def test_reset_clears_old_security_code_but_not_cooldown(mocker):
    change_mock = mocker.patch(_CHANGE, return_value=None)
    mocker.patch(_UTCNOW, return_value=_T0)

    task = student_access_code.StudentAccessCodeTask()
    async with _running(task):
        assert (
            await task.ensure_code_changed(
                auto_control_enabled=True, last_received_security_code=_OLD_CODE
            )
            is False
        )

        task.reset()

        # old_security_code was forgotten, so the same code now looks
        # "fresh" again...
        assert (
            await task.ensure_code_changed(
                auto_control_enabled=True, last_received_security_code=_OLD_CODE
            )
            is False
        )

        # ...but the cooldown clock was not reset: a change request made
        # right afterwards (same mocked instant) still gets skipped.
        assert await task.request_change() is False

    change_mock.assert_awaited_once()


@pytest.mark.anyio
async def test_reset_clears_api_reported_security_code(mocker):
    change_mock = mocker.patch(_CHANGE, return_value=_NEW_CODE)
    mocker.patch(_UTCNOW, return_value=_T0)

    task = student_access_code.StudentAccessCodeTask()
    async with _running(task):
        assert await task.request_change() is True
        assert task.api_reported_security_code() == _NEW_CODE

        task.reset()

        assert task.api_reported_security_code() is None

        # The previously-learned new code must not short-circuit this
        # call; it has to go through the normal wait again.
        assert (
            await task.ensure_code_changed(
                auto_control_enabled=True, last_received_security_code=_OLD_CODE
            )
            is False
        )

    change_mock.assert_awaited_once()
