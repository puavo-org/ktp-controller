# Standard library imports
import argparse
import logging
import os
import os.path
import pathlib
import re
import subprocess
import typing

# Third-party imports
import validators

import ktp_controller.asyncio
import ktp_controller.net
import ktp_controller.puavo.conf
import ktp_controller.utils

# Internal imports
from ktp_controller import VERSION

_LOGGER = logging.getLogger(os.path.basename(__file__))
_THIS_DIR = os.path.dirname(__file__)

_NAKSU2_CERTS_DIR_PATH = os.path.expanduser("~/.local/share/digabi/naksu2/certs/")


def _read_abitti2server_domain_name() -> str | None:
    try:
        with open(
            os.path.join(_NAKSU2_CERTS_DIR_PATH, "domain.txt"),
            encoding="utf-8",
        ) as domain_file:
            domain_name = domain_file.readline().strip()
    except FileNotFoundError:
        return None

    if not validators.domain(domain_name):
        raise RuntimeError("invalid domain name", domain_name)

    if not domain_name.endswith(".koe.abitti.net"):
        raise RuntimeError("invalid domain name", domain_name)

    return domain_name


def _reset_abitti2server_domain_name() -> None:
    fqdn = _read_abitti2server_domain_name()
    if fqdn:
        _run_networking("set_domain", fqdn)
    else:
        _run_networking("del_domain")


def _get_wd(name: str) -> str:
    if not re.match(r"^[a-z0-9]{1,32}$", name):
        raise ValueError("invalid working directory name", name)

    wd = os.path.join(os.path.expanduser("~/.puavo/puavo-ers/ktp-controller"), name)

    try:
        os.makedirs(wd)
    except FileExistsError:
        pass

    return wd


def _run(prog_args: list[str], wd: str) -> None:
    with (
        open(os.path.join(wd, "stderr.log"), "w", encoding="utf-8") as stderr,
        open(os.path.join(wd, "stdout.log"), "w", encoding="utf-8") as stdout,
    ):
        subprocess.check_call(
            prog_args,
            cwd=wd,
            stdout=stdout,
            stderr=stderr,
        )


def _run_networking(*args: str) -> None:
    return _run(
        [
            "sudo",
            "-n",
            "/opt/ktp-controller/bin/ktp-controller-networking",
            *list(args),
        ],
        _get_wd("networking"),
    )


def _start_naksu2_certs_dir_monitor(
    loop: typing.Any,
) -> ktp_controller.asyncio.FileMonitor:
    pathlib.Path(_NAKSU2_CERTS_DIR_PATH).mkdir(parents=True, exist_ok=True)

    naksu2_certs_dir_monitor = ktp_controller.asyncio.FileMonitor(
        loop,
        _NAKSU2_CERTS_DIR_PATH,
        _naksu2_certs_changed,
    )

    naksu2_certs_dir_monitor.start()

    return naksu2_certs_dir_monitor


async def _naksu2_certs_changed(event: typing.Any) -> None:
    _LOGGER.info("ainotify event: %s", event)
    _reset_abitti2server_domain_name()


def _main(args: argparse.Namespace) -> int:
    try:
        ers_mode = ktp_controller.puavo.conf.get_ers_mode()
    except ktp_controller.puavo.conf.ValidationError:
        return 1

    if ers_mode == "abitti2server_examnet_unmanaged":
        _LOGGER.info("Not managing exam network.")
        return 0

    try:
        interface = ktp_controller.puavo.conf.get_ers_abitti2server_interface()
    except ktp_controller.puavo.conf.ValidationError as validation_error:
        _LOGGER.error("invalid configuration: %s", str(validation_error))
        return 1

    loop = ktp_controller.asyncio.new_event_loop(logger=_LOGGER)
    naksu2_certs_dir_monitor = None

    _run_networking("start")
    ktp_controller.net.wait_interface(interface, timeout=5)
    try:
        _reset_abitti2server_domain_name()
        naksu2_certs_dir_monitor = _start_naksu2_certs_dir_monitor(loop)
        loop.run_forever()
    finally:
        if naksu2_certs_dir_monitor is not None:
            naksu2_certs_dir_monitor.stop()
        loop.close()
        _run_networking("stop")

    return 0


def run() -> int:
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--version", action="version", version=VERSION)

    args = parser.parse_args()

    _LOGGER.info("KTP Controller Naksu2 Monitor v%s", VERSION)
    try:
        with ktp_controller.utils.singleton():
            return _main(args)
    finally:
        _LOGGER.info("Bye.")
