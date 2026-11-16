# Standard library imports
import logging
import subprocess

_LOGGER = logging.getLogger(__name__)
_IPSET_BIN = "ipset"


def create_ipset(name: str, default_timeout: int) -> None:
    _LOGGER.info("Creating ipset %s with default timeout %d", name, default_timeout)
    subprocess.check_call(
        [_IPSET_BIN, "create", name, "hash:ip", "timeout", str(default_timeout)]
    )


def destroy_ipset(name: str) -> None:
    _LOGGER.info("Destroying ipset %s", name)
    subprocess.check_call([_IPSET_BIN, "destroy", name])


def ipset_exists(name: str) -> bool:
    completed_process = subprocess.run(
        [_IPSET_BIN, "list", name, "-name"],
        capture_output=True,
    )
    return completed_process.returncode == 0


def flush_ipset(name: str) -> None:
    _LOGGER.info("Flushing ipset %s", name)
    subprocess.check_call([_IPSET_BIN, "flush", name])


def list_ipset_entries(name: str) -> list[tuple[str, int | None]]:
    output = subprocess.check_output([_IPSET_BIN, "list", name], timeout=5).decode()

    entries = []
    in_members = False
    for line in output.splitlines():
        if line == "Members:":
            in_members = True
            continue
        if not in_members or not line.strip():
            continue
        fields = line.split()
        timeout = int(fields[2]) if "timeout" in fields else None
        entries.append((fields[0], timeout))
    return entries


def add_ipset_entry(name: str, entry: str, timeout: int) -> None:
    _LOGGER.info("Adding %s to ipset %s with timeout %d", entry, name, timeout)
    subprocess.check_call([_IPSET_BIN, "add", name, entry, "timeout", str(timeout)])


def remove_ipset_entry(name: str, entry: str) -> None:
    _LOGGER.info("Removing %s from ipset %s", entry, name)
    subprocess.check_call([_IPSET_BIN, "del", name, entry])
