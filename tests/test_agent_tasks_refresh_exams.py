import asyncio
import os.path

import httpx2
import pytest

import ktp_controller.agent.tasks.base as task_base
import ktp_controller.agent.tasks.refresh_exams as refresh_exams
import ktp_controller.files

# CoalescingQueue


@pytest.mark.anyio
async def test_coalescing_queue_single_request_resolves():
    queue: task_base.CoalescingQueue[str, str] = task_base.CoalescingQueue()

    requester = asyncio.create_task(queue.request("payload"))
    await asyncio.sleep(0)

    batch = await queue.consume()
    assert [payload for payload, _ in batch] == ["payload"]

    task_base.resolve_all([future for _, future in batch], "result")

    assert await requester == "result"


@pytest.mark.anyio
async def test_coalescing_queue_concurrent_requests_join_one_batch():
    queue: task_base.CoalescingQueue[int, None] = task_base.CoalescingQueue()

    requesters = [asyncio.create_task(queue.request(i)) for i in range(5)]
    await asyncio.sleep(0)

    batch = await queue.consume()
    assert [payload for payload, _ in batch] == [0, 1, 2, 3, 4]

    task_base.resolve_all([future for _, future in batch], None)

    await asyncio.gather(*requesters)


@pytest.mark.anyio
async def test_coalescing_queue_request_after_consume_starts_new_batch():
    queue: task_base.CoalescingQueue[str, None] = task_base.CoalescingQueue()

    first = asyncio.create_task(queue.request("first"))
    await asyncio.sleep(0)
    first_batch = await queue.consume()

    # The first batch's run is still "in flight" (not yet resolved),
    # but a new request now starts a fresh, second batch rather than
    # joining the already-consumed first one.
    second = asyncio.create_task(queue.request("second"))
    await asyncio.sleep(0)
    second_batch = await queue.consume()

    assert [payload for payload, _ in first_batch] == ["first"]
    assert [payload for payload, _ in second_batch] == ["second"]

    task_base.resolve_all([future for _, future in first_batch], None)
    task_base.resolve_all([future for _, future in second_batch], None)
    await asyncio.gather(first, second)


@pytest.mark.anyio
async def test_coalescing_queue_reject_all_raises_in_requesters():
    queue: task_base.CoalescingQueue[str, None] = task_base.CoalescingQueue()

    requester = asyncio.create_task(queue.request("payload"))
    await asyncio.sleep(0)
    batch = await queue.consume()

    task_base.reject_all([future for _, future in batch], RuntimeError("boom"))

    with pytest.raises(RuntimeError, match="boom"):
        await requester


# _refresh_exams


@pytest.mark.anyio
async def test_refresh_exams_downloads_missing_exam_file_and_saves_info(
    mocker, testdir
):
    mocker.patch.object(
        ktp_controller.files, "_EXAM_FILE_DIR", os.path.join(testdir, "exam-files")
    )
    scheduled_exam = {
        "file_name": "exam.mex",
        "file_uuid": "11111111-1111-1111-1111-111111111111",
        "file_sha256": "deadbeef",
        "file_size": 123,
    }
    eom_exam_info = {"schedules": [scheduled_exam]}
    mocker.patch(
        "ktp_controller.examomatic.client.get_exam_info",
        return_value=eom_exam_info,
    )
    download_mock = mocker.patch("ktp_controller.examomatic.client.download_exam_file")
    save_mock = mocker.patch("ktp_controller.api.client.save_exam_info")

    await refresh_exams._refresh_exams(is_spontaneous=True)

    download_mock.assert_awaited_once()
    save_mock.assert_awaited_once_with(eom_exam_info)


@pytest.mark.anyio
async def test_refresh_exams_spontaneous_404_is_swallowed(mocker):
    request = httpx2.Request("GET", "http://examomatic.invalid")
    response = httpx2.Response(404, request=request)
    mocker.patch(
        "ktp_controller.examomatic.client.get_exam_info",
        side_effect=httpx2.HTTPStatusError(
            "not found", request=request, response=response
        ),
    )
    save_mock = mocker.patch("ktp_controller.api.client.save_exam_info")

    # Must not raise.
    await refresh_exams._refresh_exams(is_spontaneous=True)

    save_mock.assert_not_called()


# RefreshExamsTask


@pytest.mark.anyio
async def test_run_consumer_coalesces_concurrent_requests(mocker):
    call_count = 0
    started = asyncio.Event()
    gate = asyncio.Event()

    async def fake_refresh_exams(*, is_spontaneous):
        nonlocal call_count
        call_count += 1
        started.set()
        await gate.wait()

    mocker.patch(
        "ktp_controller.agent.tasks.refresh_exams._refresh_exams",
        side_effect=fake_refresh_exams,
    )

    task = refresh_exams.RefreshExamsTask(interval_sec=9999)
    consumer = asyncio.create_task(task.run_consumer())

    # This first request starts the one in-flight run.
    first = asyncio.create_task(task.request_refresh(is_spontaneous=True))
    await started.wait()
    assert call_count == 1

    # Two more requests arrive while the first run is still in
    # flight. They must coalesce into at most one more run, not two.
    second = asyncio.create_task(task.request_refresh(is_spontaneous=False))
    third = asyncio.create_task(task.request_refresh(is_spontaneous=True))
    await asyncio.sleep(0)

    gate.set()  # let every (present and future) fake_refresh_exams call return
    await asyncio.gather(first, second, third)

    assert call_count == 2

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
