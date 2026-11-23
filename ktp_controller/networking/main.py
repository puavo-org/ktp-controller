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
import signal
import typing

# Internal imports
import ktp_controller.net
import ktp_controller.networking.dnsmasq as dnsmasq
import ktp_controller.networking.firewall as firewall
import ktp_controller.networking.ipset as ipset
import ktp_controller.networking.nm as nm
import ktp_controller.nginx
import ktp_controller.puavo.conf
from ktp_controller import SETTINGS, VERSION

_THIS_NAME = "ktp-controller-networking"
_LOGGER = logging.getLogger(_THIS_NAME)
_ALLOW_TO_WAN_IPSET_DEFAULT_TIMEOUT_SECONDS = 7200


def _allow_to_wan_ipset_name(interface: str) -> str | None:
    if ipset.is_ipset_available():
        return f"allow_{interface}_to_wan"
    return None


def _create_allow_to_wan_ipset(interface: str) -> None:
    if not interface:
        return
    name = _allow_to_wan_ipset_name(interface)
    if name is None:
        return
    if ipset.ipset_exists(name):
        _LOGGER.warning(
            "ipset %s already exists, flushing it instead of creating", name
        )
        ipset.flush_ipset(name)
        return
    ipset.create_ipset(name, _ALLOW_TO_WAN_IPSET_DEFAULT_TIMEOUT_SECONDS)


def _destroy_allow_to_wan_ipset(interface: str) -> None:
    if not interface:
        return
    name = _allow_to_wan_ipset_name(interface)
    if name is None:
        return
    if ipset.ipset_exists(name):
        ipset.destroy_ipset(name)


def _enable_wan_forwarding_rules(interface: str) -> None:
    if not interface:
        return
    ipset_name = _allow_to_wan_ipset_name(interface)
    if ipset_name is None:
        return

    firewall.enable_forwarding(
        interface,
        ktp_controller.net.get_default_route_interface(),
        ipset_name,
    )
    firewall.enable_ipv6_forwarding_drop(interface, ipset_name)


def _disable_wan_forwarding_rules(interface: str) -> None:
    if not interface:
        return
    ipset_name = _allow_to_wan_ipset_name(interface)
    if ipset_name is None:
        return
    firewall.disable_forwarding(ipset_name)
    firewall.disable_ipv6_forwarding_drop(ipset_name)


def _run_regardless(
    steps: typing.Sequence[typing.Callable[[], typing.Any]], result_index: int
) -> typing.Any:
    """Run every step in order regardless of whether an earlier one raised.

    steps[result_index] supplies the return value. Steps after it run as
    pure cleanup, but a failure in one of them still overrides/propagates
    instead of being swallowed, matching ordinary nested try/finally
    semantics.
    """

    def after(i: int) -> None:
        if i >= len(steps):
            return
        try:
            steps[i]()
        finally:
            after(i + 1)

    def before(i: int) -> typing.Any:
        if i == result_index:
            try:
                return steps[i]()
            finally:
                after(i + 1)
        try:
            steps[i]()
        finally:
            return before(i + 1)  # noqa: B012 (intentional: swallow step i's failure)

    return before(0)


def _command_start(
    interface: str, network: str, number: int, args: argparse.Namespace
) -> int:
    _create_allow_to_wan_ipset(interface)

    net = ktp_controller.net.Net(interface, network, number)
    net.up()
    _enable_wan_forwarding_rules(interface)
    net.enable_forwarding()

    with open(dnsmasq.HOSTS_FILE, "w", encoding="utf-8"):
        pass  # truncate before start

    # The DHCP/DNS server must be (re)started regardless of whether
    # configuring NetworkManager succeeded.
    return typing.cast(
        int,
        _run_regardless(
            [
                nm.configure_nm_dnsmasq_plugin,
                lambda: dnsmasq.start_dhcp_dns_server(
                    net,
                    allowed_wan_domains=SETTINGS.networking_allowed_wan_domains,
                    ipset_name=_allow_to_wan_ipset_name(interface),
                    local_dns_ttl=SETTINGS.networking_local_dns_ttl,
                ),
            ],
            result_index=1,
        ),
    )


def _command_stop(
    interface: str, network: str, number: int, args: argparse.Namespace
) -> int:
    net = ktp_controller.net.Net(interface, network, number)
    # The DHCP/DNS server must be stopped and the interface brought down
    # regardless of whether unconfiguring NetworkManager failed.
    return typing.cast(
        int,
        _run_regardless(
            [
                nm.unconfigure_nm_dnsmasq_plugin,
                dnsmasq.stop_dhcp_dns_server,
                net.disable_forwarding,
                lambda: _disable_wan_forwarding_rules(interface),
                net.down,
                lambda: _destroy_allow_to_wan_ipset(interface),
            ],
            result_index=1,
        ),
    )


def _validate_nginx_args(args: argparse.Namespace) -> bool:
    nginx_args = [args.nginx_port, args.nginx_crt_filepath, args.nginx_key_filepath]
    if any(nginx_args) and not all(nginx_args):
        _LOGGER.error("all --nginx-* options must be given")
        return False
    return True


def _resolve_fqdn_ipv4_address(interface: str) -> ipaddress.IPv4Address:
    return ipaddress.IPv4Address(
        ktp_controller.net.interface_addresses(interface)["AF_INET"][0]["addr"]
    )


def _write_dnsmasq_hosts_entry(ipv4_addr: ipaddress.IPv4Address, fqdn: str) -> None:
    with open(dnsmasq.HOSTS_FILE, "w", encoding="utf-8") as dnsmasq_hosts_file:
        dnsmasq_hosts_file.write(f"{ipv4_addr} {fqdn}\n")


def _command_set_domain(
    interface: str, network: str, number: int, args: argparse.Namespace
) -> int:

    if not _validate_nginx_args(args):
        return 1

    ipv4_addr = _resolve_fqdn_ipv4_address(interface)
    _write_dnsmasq_hosts_entry(ipv4_addr, args.FQDN)

    def _maybe_enable_nginx_wui_tls_reverse_proxy() -> None:
        if args.nginx_port and args.nginx_crt_filepath and args.nginx_key_filepath:
            ktp_controller.nginx.enable_nginx_wui_tls_reverse_proxy(
                args.FQDN,
                args.nginx_port,
                args.nginx_crt_filepath,
                args.nginx_key_filepath,
            )

    # dnsmasq must always be signalled to reload regardless of whether
    # reloading NetworkManager failed.
    return typing.cast(
        int,
        _run_regardless(
            [
                nm.reload_networkmanager,
                _maybe_enable_nginx_wui_tls_reverse_proxy,
                lambda: int(dnsmasq.kill_dnsmasq(signal.SIGHUP)),
            ],
            result_index=2,
        ),
    )


def _command_del_domain(
    interface: str, network: str, number: int, args: argparse.Namespace
) -> int:
    with open(dnsmasq.HOSTS_FILE, "w", encoding="utf-8"):
        pass  # just truncate

    # dnsmasq must always be signalled to reload regardless of whether
    # reloading NetworkManager failed.
    return typing.cast(
        int,
        _run_regardless(
            [
                nm.reload_networkmanager,
                ktp_controller.nginx.disable_nginx_wui_tls_reverse_proxy,
                lambda: int(dnsmasq.kill_dnsmasq(signal.SIGHUP)),
            ],
            result_index=2,
        ),
    )


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
