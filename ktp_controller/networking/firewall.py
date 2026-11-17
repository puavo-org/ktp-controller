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


def enable_forwarding(lan: str, wan: str | None, ipset_name: str) -> None:
    chain = ipset_name
    comment = ipset_name

    require_interface(wan)
    assert wan is not None  # require_interface() raised otherwise
    require_interface(lan)
    if wan == lan:
        raise ValueError("WAN and LAN interface must be different", wan)

    _LOGGER.info("recreating filter chain %r", chain)
    remove_rules_by_comment("nat", "POSTROUTING", comment)
    remove_rules_by_comment("filter", "FORWARD", comment)
    recreate_chain("filter", chain)

    # Log new allowlisted flows (rate-limited to avoid log flooding)
    add_rule(
        "filter",
        chain,
        "--match",
        "conntrack",
        "--ctstate",
        "NEW",
        "--match",
        "set",
        "--match-set",
        ipset_name,
        "dst",
        "--match",
        "limit",
        "--limit",
        "30/second",
        "--limit-burst",
        "100",
        "--jump",
        "LOG",
        "--log-prefix",
        f"{ipset_name} ",
        "--log-level",
        "6",
    )

    # Allow only ipset allowlisted destinations
    add_rule(
        "filter",
        chain,
        "--match",
        "set",
        "--match-set",
        ipset_name,
        "dst",
        "--jump",
        "ACCEPT",
    )

    # Drop everything else
    add_rule("filter", chain, "--jump", "DROP")

    # Allow return traffic for established connections
    add_rule(
        "filter",
        "FORWARD",
        "--in-interface",
        wan,
        "--out-interface",
        lan,
        "--match",
        "comment",
        "--comment",
        comment,
        "--match",
        "conntrack",
        "--ctstate",
        "RELATED,ESTABLISHED",
        "--jump",
        "ACCEPT",
    )

    # Enforce allowlist for new LAN->WAN traffic
    add_rule(
        "filter",
        "FORWARD",
        "--in-interface",
        lan,
        "--out-interface",
        wan,
        "--match",
        "comment",
        "--comment",
        comment,
        "--jump",
        chain,
    )

    # NAT only for allowlisted destinations
    add_rule(
        "nat",
        "POSTROUTING",
        "--out-interface",
        wan,
        "--match",
        "comment",
        "--comment",
        comment,
        "--match",
        "set",
        "--match-set",
        ipset_name,
        "dst",
        "--jump",
        "MASQUERADE",
    )

    _LOGGER.info("internet forwarding enabled: LAN %r -> WAN %r", lan, wan)


def disable_forwarding(ipset_name: str) -> None:
    chain = ipset_name
    comment = ipset_name

    _LOGGER.info("removing forwarding rules")
    remove_rules_by_comment("nat", "POSTROUTING", comment)
    remove_rules_by_comment("filter", "FORWARD", comment)
    flush_and_delete_chain("filter", chain)
