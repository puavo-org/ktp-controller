# Standard library imports
import logging
import shlex
import subprocess

# Internal imports
import ktp_controller.net

_LOGGER = logging.getLogger(__name__)
_IPTABLES_BIN = "iptables"


def require_interface(interface: str | None) -> None:
    if not interface or interface not in ktp_controller.net.interfaces():
        raise ValueError("interface does not exist", interface)


def chain_exists(table: str, chain: str) -> bool:
    completed_process = subprocess.run(
        [_IPTABLES_BIN, "-t", table, "-L", chain, "-n"],
        capture_output=True,
    )
    return completed_process.returncode == 0


def create_chain(table: str, chain: str) -> None:
    subprocess.check_call([_IPTABLES_BIN, "-t", table, "-N", chain])


def flush_chain(table: str, chain: str) -> None:
    subprocess.check_call([_IPTABLES_BIN, "-t", table, "-F", chain])


def delete_chain(table: str, chain: str) -> None:
    subprocess.check_call([_IPTABLES_BIN, "-t", table, "-X", chain])


def recreate_chain(table: str, chain: str) -> None:
    if chain_exists(table, chain):
        flush_chain(table, chain)
        delete_chain(table, chain)
    create_chain(table, chain)


def add_rule(table: str, chain: str, *rule_args: str) -> None:
    subprocess.check_call([_IPTABLES_BIN, "-t", table, "-A", chain, *rule_args])


def remove_rules_by_comment(table: str, chain: str, comment: str) -> None:
    output = subprocess.check_output([_IPTABLES_BIN, "-t", table, "-S", chain]).decode()
    needle = f'--comment "{comment}"'
    for line in output.splitlines():
        if needle not in line:
            continue
        tokens = shlex.split(line)
        tokens[0] = "-D"
        subprocess.check_call([_IPTABLES_BIN, "-t", table, *tokens])


def flush_and_delete_chain(table: str, chain: str) -> None:
    if not chain_exists(table, chain):
        return
    flush_chain(table, chain)
    delete_chain(table, chain)
