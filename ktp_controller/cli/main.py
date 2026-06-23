# Standard library imports
import argparse
import asyncio
import typing

# Third-party imports
import yaml

# Internal imports
from ktp_controller import VERSION


async def _command_api_async_command(args: argparse.Namespace) -> str:
    import ktp_controller.api.client

    return await ktp_controller.api.client.async_command(args.COMMAND)


def _print_as_yaml(obj: typing.Any) -> None:
    print(
        yaml.dump(
            obj,
            default_flow_style=False,
            sort_keys=False,
        )
    )


def _agofy(last_status_report: dict[str, typing.Any]) -> None:
    import ktp_controller.utils

    if last_status_report["reported_at"] is not None:
        reported_at_ago = ktp_controller.utils.ago(last_status_report["reported_at"])
        last_status_report["reported_at"] += f" ({reported_at_ago})"

    created_at_ago = ktp_controller.utils.ago(last_status_report["created_at"])
    last_status_report["created_at"] += f" ({created_at_ago})"

    ktp_controller_started_at_ago = ktp_controller.utils.ago(
        last_status_report["ktp_controller"]["started_at"]
    )
    last_status_report["ktp_controller"]["started_at"] += (
        f" ({ktp_controller_started_at_ago})"
    )

    ep = last_status_report["ktp_controller"]["current_exam_package"]
    if ep is not None:
        for f in ("state_changed_at", "started_at", "archived_at"):
            if ep[f] is not None:
                ep[f] += f" ({ktp_controller.utils.ago(ep[f])})"

    for ex in last_status_report["abitti2"]["exams"] or []:
        for f in ("started_at",):
            if ex[f] is not None:
                ex[f] += f" ({ktp_controller.utils.ago(ex[f])})"

    if last_status_report["abitti2"]["last_message_received_at"] is not None:
        abitti2_last_message_received_at_ago = ktp_controller.utils.ago(
            last_status_report["abitti2"]["last_message_received_at"]
        )
        last_status_report["abitti2"]["last_message_received_at"] += (
            f" ({abitti2_last_message_received_at_ago})"
        )


async def _command_status(args: argparse.Namespace) -> None:
    import ktp_controller.api.client

    current_exam_package = await ktp_controller.api.client.get_current_exam_package()
    last_status_report = await ktp_controller.api.client.get_last_status_report()

    if current_exam_package is None:
        print("# Current exam package: -")
    else:
        print("# Current exam package:")
        scheduled_exam_external_ids = current_exam_package.pop(
            "scheduled_exam_external_ids"
        )
        for scheduled_exam_external_id in scheduled_exam_external_ids:
            scheduled_exam = await ktp_controller.api.client.get_scheduled_exam(
                scheduled_exam_external_id
            )
            current_exam_package.setdefault("scheduled_exams", []).append(
                scheduled_exam
            )
        _print_as_yaml(current_exam_package)
    print()
    if last_status_report is None:
        print("# Last status report: -")
    else:
        print("# Last status report:")

        _agofy(last_status_report)
        if not args.show_cached_files:
            last_status_report["ktp_controller"].pop("cached_files")
        _print_as_yaml(last_status_report)
    print()

    return


_COMMANDS: dict[
    str, typing.Callable[[argparse.Namespace], typing.Awaitable[str | None]]
] = {
    "enable_auto_control": _command_api_async_command,
    "disable_auto_control": _command_api_async_command,
    "start_current_exam_package": _command_api_async_command,
    "stop_current_exam_package": _command_api_async_command,
    "archive_current_exam_package": _command_api_async_command,
    "prepare_current_exam_package": _command_api_async_command,
    "crash_agent": _command_api_async_command,
    "status": _command_status,
}

_COMMAND_ARGUMENTS: dict[str, tuple[tuple[str, ...], dict[str, typing.Any]]] = {
    "status": (
        ("--show-cached-files",),
        {"help": "show cached files", "action": "store_true", "default": False},
    ),
}


async def _dispatch_command(args: argparse.Namespace) -> int:
    # Lazily imported here to avoid long start-up time of this script.
    import websockets

    import ktp_controller.api.client
    import ktp_controller.messages
    import ktp_controller.utils

    command_result_data = None

    async with websockets.connect(
        ktp_controller.api.client.get_ui_websock_url()
    ) as ui_websock:
        command_uuid: str | None = await _COMMANDS[args.COMMAND](args)
        if command_uuid is not None:
            async for data in ui_websock:
                try:
                    message_dict = ktp_controller.utils.json_loads_dict(data)
                except ValueError:
                    # Most probably a programming error, API should not
                    # send invalid JSON to agents.
                    print(f"API sent invalid JSON data: {data!r}")
                    continue
                if message_dict["kind"] != "command_result":
                    continue
                command_result_message = (
                    ktp_controller.messages.CommandResultMessage.model_validate(
                        message_dict
                    )
                )
                command_result_data = command_result_message.data
                if str(command_result_data.command_uuid) != command_uuid:
                    continue
                break

    if command_result_data is not None and not command_result_data.command_status.is_ok:
        print(f"ERROR: {args.COMMAND} failed: {command_result_data.error_message}")
        return 1

    return 0


def run_command(args: argparse.Namespace) -> int:
    return asyncio.run(_dispatch_command(args))


def run() -> int:
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--version", action="version", version=VERSION)
    subparsers = parser.add_subparsers(title="Commands", dest="COMMAND", required=True)
    for command in _COMMANDS:
        subparser = subparsers.add_parser(command)
        try:
            cmd_args, cmd_kwargs = _COMMAND_ARGUMENTS[command]
        except KeyError:
            pass
        else:
            subparser.add_argument(*cmd_args, **cmd_kwargs)

    args = parser.parse_args()

    return run_command(args)
