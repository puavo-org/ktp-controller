# This script is used for managing Abitti2 server networking. It reads
# following Puavo conf options:
#
#   puavo.ers.abitti2server.interface
#   puavo.ers.abitti2server.network
#   puavo.ers.abitti2server.number
#
# Please see puavo-ers.json for more info about these conf options.
#
# Assuming aforementioned Puavo configuration is set, this script can
# be used like so:
#
# To setup the network interface and start dnsmasq server, run:
#   puavo-ers-abitti2server-networking start
#
# To stop the dnsmasq, run:
#   puavo-ers-abitti2server-networking stop
#
# To set a A-record for the current host, run:
#   puavo-ers-abitti2server-networking set_domain mydomain.example.invalid
#
# To delete the A-record, run:
#   puavo-ers-abitti2server-networking del_domain
#

# Standard library imports
import argparse
import ipaddress
import logging
import os
import os.path
import signal
import subprocess
import time
import typing

import ktp_controller.net
import ktp_controller.puavo.conf

# Internal imports
from ktp_controller import VERSION

_THIS_NAME = "ktp-controller-networking"
_LOGGER = logging.getLogger(_THIS_NAME)
_DNSMASQ_PID_FILE = f"/run/{_THIS_NAME}-dnsmasq.pid"
_DNSMASQ_LEASES_FILE = f"/var/lib/{_THIS_NAME}-dnsmasq.leases"
_DNSMASQ_HOSTS_FILE = f"/var/lib/{_THIS_NAME}-dnsmasq.hosts"
_LOCAL_DOMAIN = "ktp-controller.invalid"
_NM_CONF_FILE = "/etc/NetworkManager/dnsmasq.d/puavo-ers.conf"


_KOE_ABITTI_NET_DNS_SERVERS = [
    "9.9.9.9",
    "1.1.1.1",
    "8.8.8.8",
]


def _start_dhcp_dns_server(net: ktp_controller.net.Net) -> int:
    args = [
        "dnsmasq",
        "--port=53",
        f"--listen-address={net.host_address}",
        f"--domain={_LOCAL_DOMAIN},{net.network},local",
        "--domain-needed",
        "--bogus-priv",
        "--no-resolv",
        "--no-hosts",
        "--expand-hosts",
        "--bind-interfaces",
        f"--dhcp-leasefile={_DNSMASQ_LEASES_FILE}",
        f"--dhcp-range={net.dhcp_hosts[0]},{net.dhcp_hosts[-1]},12h",
        "--dhcp-option=option:router",  # Removes option:router from responses; there's no way out from this network
        "--log-queries",
        "--log-dhcp",
        "--log-debug",
        f"--pid-file={_DNSMASQ_PID_FILE}",
        f"--addn-hosts={_DNSMASQ_HOSTS_FILE}",
    ]

    args.extend(
        f"--server=/koe.abitti.net/{koe_abitti_net_dns_server}"
        for koe_abitti_net_dns_server in _KOE_ABITTI_NET_DNS_SERVERS
    )
    if len(_KOE_ABITTI_NET_DNS_SERVERS) > 0:
        args.append("--all-servers")

    try:
        user = os.environ["SUDO_USER"]
    except KeyError:
        # Let dnsmasq switch uid to it's default, normally nobody
        pass
    else:
        # Ensure no tricks are being played, that the user actually exists.
        user = subprocess.check_output(["id", "-un", user], timeout=2).decode().strip()
        args.append(f"--user={user}")
    _LOGGER.info("Spawning dnsmasq with args: %s", args)
    subprocess.check_call(args)

    return 0


def _kill_dnsmasq(sig: int) -> bool:
    with open(_DNSMASQ_PID_FILE, encoding="ascii") as dnsmasq_pid_file:
        dnsmasq_pid = int(dnsmasq_pid_file.read().strip())

    try:
        os.kill(dnsmasq_pid, sig)
    except ProcessLookupError:
        os.unlink(_DNSMASQ_PID_FILE)
        return True

    return False


def _stop_dhcp_dns_server() -> int:
    # First gently.
    if _kill_dnsmasq(15):
        return 0

    # Give it some time to die.
    for _ in range(4):
        time.sleep(0.5)
        if _kill_dnsmasq(0):
            return 0

    # Then with force.
    if _kill_dnsmasq(9):
        _LOGGER.error("failed to kill dnsmasq gracefully!")
        return 1

    _LOGGER.critical("failed to kill dnsmasq!")
    return 1


def _reload_networkmanager() -> None:
    completed_process = subprocess.run(
        ["systemctl", "reload", "NetworkManager.service"],
        capture_output=True,
    )
    if completed_process.returncode != 0:
        _LOGGER.warning(
            "failed to reload NetworkManager: %s", completed_process.stderr.decode()
        )


def _configure_networkmanager() -> None:
    """Best-effort inclusion of the domain record in the local DNS controlled by NetworkManager"""
    try:
        with open(f"{_NM_CONF_FILE}.tmp", "w", encoding="utf-8") as nm_conf_file:
            print(f"addn-hosts={_DNSMASQ_HOSTS_FILE}", file=nm_conf_file)
            for koe_abitti_net_dns_server in _KOE_ABITTI_NET_DNS_SERVERS:
                print(
                    f"server=/koe.abitti.net/{koe_abitti_net_dns_server}",
                    file=nm_conf_file,
                )
            if len(_KOE_ABITTI_NET_DNS_SERVERS) > 0:
                print("all-servers", file=nm_conf_file)
    except FileNotFoundError:
        # This means that /etc/NetworkManager/dnsmasq.d does not
        # exist, which tells us that NetworkManager is most probably
        # not being used on this host. And that's fine, then we are
        # not doing anything.
        _LOGGER.warning(
            "/etc/NetworkManager/dnsmasq.d/ does not exist, "
            "not configuring NetworkManager",
            _NM_CONF_FILE,
        )
        return
    os.rename(f"{_NM_CONF_FILE}.tmp", _NM_CONF_FILE)

    _reload_networkmanager()


def _unconfigure_networkmanager() -> None:
    try:
        os.unlink(_NM_CONF_FILE)
    except FileNotFoundError:
        return  # A bit weird situation, but that's ok.

    _reload_networkmanager()


def _command_start(
    interface: str, network: str, number: int, args: argparse.Namespace
) -> int:
    net = ktp_controller.net.Net(interface, network, number)
    net.up()

    with open(_DNSMASQ_HOSTS_FILE, "w", encoding="utf-8"):
        pass  # truncate before start

    try:
        _configure_networkmanager()
    finally:
        # The DHCP/DNS server must be (re)started regardless of whether
        # configuring NetworkManager succeeded.
        return _start_dhcp_dns_server(net)  # noqa: B012


def _command_stop(
    interface: str, network: str, number: int, args: argparse.Namespace
) -> int:
    net = ktp_controller.net.Net(interface, network, number)
    try:
        _unconfigure_networkmanager()
    finally:
        # The DHCP/DNS server must be stopped and the interface brought
        # down regardless of whether unconfiguring NetworkManager failed.
        try:
            return _stop_dhcp_dns_server()  # noqa: B012
        finally:
            net.down()


def _command_set_domain(
    interface: str, network: str, number: int, args: argparse.Namespace
) -> int:
    ipv4_addr = ipaddress.IPv4Address(
        ktp_controller.net.interface_addresses(interface)["AF_INET"][0]["addr"]
    )
    with open(_DNSMASQ_HOSTS_FILE, "w", encoding="utf-8") as dnsmasq_hosts_file:
        dnsmasq_hosts_file.write(f"{ipv4_addr} {args.FQDN}\n")

    try:
        _reload_networkmanager()
    finally:
        # dnsmasq must always be signalled to reload regardless of whether
        # reloading NetworkManager failed.
        return int(_kill_dnsmasq(signal.SIGHUP))  # noqa: B012


def _command_del_domain(
    interface: str, network: str, number: int, args: argparse.Namespace
) -> int:
    with open(_DNSMASQ_HOSTS_FILE, "w", encoding="utf-8"):
        pass  # just truncate

    try:
        _reload_networkmanager()
    finally:
        # dnsmasq must always be signalled to reload regardless of whether
        # reloading NetworkManager failed.
        return int(_kill_dnsmasq(signal.SIGHUP))  # noqa: B012


def _main() -> int:
    argparser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="KTP Controller Networking",
    )

    argparser.add_argument("--version", action="version", version=VERSION)

    subparsers = argparser.add_subparsers(dest="COMMAND", help="Available commands")

    parser_start = subparsers.add_parser("start")
    parser_start.set_defaults(func=_command_start)

    parser_stop = subparsers.add_parser("stop")
    parser_stop.set_defaults(func=_command_stop)

    parser_set_domain = subparsers.add_parser("set_domain")
    parser_set_domain.add_argument("FQDN")
    parser_set_domain.set_defaults(func=_command_set_domain)

    parser_del_domain = subparsers.add_parser("del_domain")
    parser_del_domain.set_defaults(func=_command_del_domain)

    args = argparser.parse_args()

    try:
        interface = ktp_controller.puavo.conf.get_ers_abitti2server_interface()
        network = ktp_controller.puavo.conf.get_ers_abitti2server_network()
        number = ktp_controller.puavo.conf.get_ers_abitti2server_number()
    except ktp_controller.puavo.conf.ValidationError as validation_error:
        _LOGGER.error("invalid configuration: %s", str(validation_error))
        return 1

    if os.getuid() != 0:
        _LOGGER.error("must be root")
        return 1

    signal.signal(signal.SIGINT, signal.SIG_IGN)

    if hasattr(args, "func"):
        return typing.cast(int, args.func(interface, network, number, args))

    argparser.print_help()
    return 1


def run() -> int:
    _LOGGER.info("KTP Controller Networking v%s", VERSION)
    try:
        return _main()
    finally:
        _LOGGER.info("Bye.")
