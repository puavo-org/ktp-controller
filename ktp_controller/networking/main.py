# This script is used for managing Abitti2 server networking. It reads
# following Puavo conf options:
#
#   puavo.ers.abitti2server.interface
#   puavo.ers.abitti2server.network
#   puavo.ers.abitti2server.number
#
# Please see /usr/share/puavo-conf/definitions/puavo-ers.json for more
# info about these conf options.
#
# Assuming aforementioned Puavo configuration is set, this script can
# be used like so:
#
# To setup the network interface and start dnsmasq server, run:
#   ktp-controller-networking start
#
# To stop the dnsmasq, run:
#   ktp-controller-networking stop
#
# To set a A-record for the current host, run:
#   ktp-controller-networking set_domain mydomain.example.invalid
#
# To delete the A-record, run:
#   ktp-controller-networking del_domain
#

# Standard library imports
import argparse
import ipaddress
import logging
import os
import os.path
import signal
import subprocess
import typing

# Internal imports
import ktp_controller.net
import ktp_controller.networking.dnsmasq as dnsmasq
import ktp_controller.nginx
import ktp_controller.puavo.conf
from ktp_controller import VERSION

_THIS_NAME = "ktp-controller-networking"
_LOGGER = logging.getLogger(_THIS_NAME)
_NM_CONF_FILE = "/etc/NetworkManager/dnsmasq.d/puavo-ers.conf"


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
            print(f"address=/{dnsmasq._LOCAL_DOMAIN}/::", file=nm_conf_file)
            print(f"addn-hosts={dnsmasq._DNSMASQ_HOSTS_FILE}", file=nm_conf_file)
            for koe_abitti_net_dns_server in dnsmasq._KOE_ABITTI_NET_DNS_SERVERS:
                print(
                    f"server=/koe.abitti.net/{koe_abitti_net_dns_server}",
                    file=nm_conf_file,
                )
            if len(dnsmasq._KOE_ABITTI_NET_DNS_SERVERS) > 0:
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

    with open(dnsmasq._DNSMASQ_HOSTS_FILE, "w", encoding="utf-8"):
        pass  # truncate before start

    try:
        _configure_networkmanager()
    finally:
        # The DHCP/DNS server must be (re)started regardless of whether
        # configuring NetworkManager succeeded.
        return dnsmasq._start_dhcp_dns_server(net)  # noqa: B012


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
            return dnsmasq._stop_dhcp_dns_server()  # noqa: B012
        finally:
            net.down()


def _command_set_domain(
    interface: str, network: str, number: int, args: argparse.Namespace
) -> int:

    nginx_args = [args.nginx_port, args.nginx_crt_filepath, args.nginx_key_filepath]

    if any(nginx_args) and not all(nginx_args):
        _LOGGER.error("all --nginx-* options must be given")
        return 1

    ipv4_addr = ipaddress.IPv4Address(
        ktp_controller.net.interface_addresses(interface)["AF_INET"][0]["addr"]
    )
    with open(dnsmasq._DNSMASQ_HOSTS_FILE, "w", encoding="utf-8") as dnsmasq_hosts_file:
        dnsmasq_hosts_file.write(f"{ipv4_addr} {args.FQDN}\n")

    try:
        _reload_networkmanager()
    finally:
        try:
            if args.nginx_port and args.nginx_crt_filepath and args.nginx_key_filepath:
                ktp_controller.nginx.enable_nginx_wui_tls_reverse_proxy(
                    args.FQDN,
                    args.nginx_port,
                    args.nginx_crt_filepath,
                    args.nginx_key_filepath,
                )
        finally:
            # dnsmasq must always be signalled to reload regardless of whether
            # reloading NetworkManager failed.
            return int(dnsmasq._kill_dnsmasq(signal.SIGHUP))  # noqa: B012


def _command_del_domain(
    interface: str, network: str, number: int, args: argparse.Namespace
) -> int:
    with open(dnsmasq._DNSMASQ_HOSTS_FILE, "w", encoding="utf-8"):
        pass  # just truncate

    try:
        _reload_networkmanager()
    finally:
        try:
            ktp_controller.nginx.disable_nginx_wui_tls_reverse_proxy()
        finally:
            # dnsmasq must always be signalled to reload regardless of whether
            # reloading NetworkManager failed.
            return int(dnsmasq._kill_dnsmasq(signal.SIGHUP))  # noqa: B012


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
    parser_set_domain.add_argument("--nginx-port", type=int, choices=range(1, 65536))
    parser_set_domain.add_argument("--nginx-crt-filepath", type=str)
    parser_set_domain.add_argument("--nginx-key-filepath", type=str)
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
