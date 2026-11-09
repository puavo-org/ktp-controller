import asyncio
import contextlib
import dataclasses
import datetime

import pytest

import ktp_controller.agent.tasks.base as task_base
import ktp_controller.agent.tasks.status_report as status_report

_T0 = datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC)


def _inputs(*, utcnow: datetime.datetime = _T0) -> status_report.StatusReportInputs:
    return status_report.StatusReportInputs(
        utcnow=utcnow,
        supervisor_passphrase="passphrase",
        domain="example.invalid",
        abitti2_version="1.2.3",
        cert=None,
        current_exam_package=None,
        next_exam_packages=[],
        exam_stats=None,
        ktp_controller_stats=None,
        cached_files=[],
        answer_count=None,
        student_access_code=None,
        last_message_from_abitti2_received_at=None,
        exams=None,
        students=None,
        settings={},
        started_at=None,
        is_auto_control_enabled=False,
        os_stats={},
        os_release="release",
        puavo_os_image_name=None,
        puavo_os_image_release=None,
    )


@contextlib.asynccontextmanager
async def _running(task: status_report.StatusReportTask):
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


# DirtySignal


@pytest.mark.anyio
async def test_dirty_signal_wait_returns_once_marked_dirty():
    signal = task_base.DirtySignal()
    signal.mark_dirty()

    # Must not raise/hang: the signal is already dirty.
    await asyncio.wait_for(signal.wait_dirty_or_timeout(9999), timeout=1)


@pytest.mark.anyio
async def test_dirty_signal_wait_times_out_when_not_dirty():
    signal = task_base.DirtySignal()

    # Must return (via the timeout path) rather than hang forever.
    await asyncio.wait_for(signal.wait_dirty_or_timeout(0), timeout=1)


@pytest.mark.anyio
async def test_dirty_signal_clears_after_wait():
    signal = task_base.DirtySignal()
    signal.mark_dirty()
    await signal.wait_dirty_or_timeout(9999)

    waiter = asyncio.create_task(signal.wait_dirty_or_timeout(9999))
    await asyncio.sleep(0)
    assert not waiter.done()

    signal.mark_dirty()
    await asyncio.wait_for(waiter, timeout=1)


@pytest.mark.anyio
async def test_dirty_signal_concurrent_mark_dirty_wakes_single_waiter():
    signal = task_base.DirtySignal()
    waiter = asyncio.create_task(signal.wait_dirty_or_timeout(9999))
    await asyncio.sleep(0)

    signal.mark_dirty()
    signal.mark_dirty()
    signal.mark_dirty()

    await asyncio.wait_for(waiter, timeout=1)


# build_status_report


def test_build_status_report_shape():
    report = status_report.build_status_report(
        dataclasses.replace(_inputs(utcnow=_T0), answer_count=3)
    )

    assert report["created_at"] == _T0
    assert report["abitti2"]["answer_count"] == 3
    assert report["abitti2"]["version"] == "1.2.3"
    assert report["ktp_controller"]["is_auto_control_enabled"] is False
    assert report["os"]["release"] == "release"
    assert "reported_at" not in report


# StatusReportTask


@pytest.mark.anyio
async def test_mark_dirty_triggers_build_and_save(mocker):
    build_inputs_mock = mocker.AsyncMock(return_value=_inputs())
    send_mock = mocker.patch("ktp_controller.examomatic.client.send_status_report")
    save_mock = mocker.patch("ktp_controller.api.client.save_status_report")

    task = status_report.StatusReportTask(
        min_examomatic_interval_sec=30, build_inputs=build_inputs_mock
    )

    async with _running(task):
        assert task.get_last_report() is None

        task.mark_dirty()
        for _ in range(100):
            if task.get_last_report() is not None:
                break
            await asyncio.sleep(0)

    build_inputs_mock.assert_awaited()
    send_mock.assert_awaited_once()
    save_mock.assert_awaited_once()
    assert task.get_last_report() is not None
    assert task.get_last_report()["reported_at"] == _T0


@pytest.mark.anyio
async def test_examomatic_send_is_throttled_but_api_save_is_not(mocker):
    build_inputs_mock = mocker.AsyncMock(
        side_effect=[
            _inputs(utcnow=_T0),
            _inputs(utcnow=_T0 + datetime.timedelta(seconds=1)),
        ]
    )
    send_mock = mocker.patch("ktp_controller.examomatic.client.send_status_report")
    save_mock = mocker.patch("ktp_controller.api.client.save_status_report")

    task = status_report.StatusReportTask(
        min_examomatic_interval_sec=30, build_inputs=build_inputs_mock
    )

    async with _running(task):
        task.mark_dirty()
        for _ in range(100):
            if save_mock.await_count >= 1:
                break
            await asyncio.sleep(0)

        task.mark_dirty()
        for _ in range(100):
            if save_mock.await_count >= 2:
                break
            await asyncio.sleep(0)

    send_mock.assert_awaited_once()
    assert save_mock.await_count == 2
    assert task.get_last_report()["reported_at"] is None


@pytest.mark.anyio
async def test_mark_expired_is_visible_via_has_last_report_expired(mocker):
    mocker.patch("ktp_controller.examomatic.client.send_status_report")
    mocker.patch("ktp_controller.api.client.save_status_report")

    task = status_report.StatusReportTask(
        min_examomatic_interval_sec=30,
        build_inputs=mocker.AsyncMock(return_value=_inputs()),
    )

    async with _running(task):
        task.mark_dirty()
        for _ in range(100):
            if task.get_last_report() is not None:
                break
            await asyncio.sleep(0)

        assert not task.has_last_report_expired()
        task.mark_expired()
        assert task.has_last_report_expired()
