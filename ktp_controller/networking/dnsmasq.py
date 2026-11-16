# Standard library imports
import logging
import os
import subprocess
import time

# Internal imports
import ktp_controller.net

_THIS_NAME = "ktp-controller-networking"
_LOGGER = logging.getLogger(__name__)
_DNSMASQ_PID_FILE = f"/run/{_THIS_NAME}-dnsmasq.pid"
_DNSMASQ_LEASES_FILE = f"/var/lib/{_THIS_NAME}-dnsmasq.leases"
_DNSMASQ_HOSTS_FILE = f"/var/lib/{_THIS_NAME}-dnsmasq.hosts"
_DNSMASQ_CONF_FILE = f"/var/lib/{_THIS_NAME}-dnsmasq.conf"
_LOCAL_DOMAIN = "koe.abitti.net"


_KOE_ABITTI_NET_DNS_SERVERS = [
    "9.9.9.9",
    "1.1.1.1",
    "8.8.8.8",
]


def _render_koe_abitti_net_dns_lines() -> list[str]:
    lines = [
        f"server=/{_LOCAL_DOMAIN}/{koe_abitti_net_dns_server}"
        for koe_abitti_net_dns_server in _KOE_ABITTI_NET_DNS_SERVERS
    ]
    if len(_KOE_ABITTI_NET_DNS_SERVERS) > 0:
        lines.append("all-servers")
    return lines


def _start_dhcp_dns_server(net: ktp_controller.net.Net) -> int:
    conf_lines = [
        "port=53",
        f"listen-address={net.host_address}",
        f"domain={_LOCAL_DOMAIN},{net.network}",
        "domain-needed",
        "bogus-priv",
        "no-hosts",
        "bind-interfaces",
        "except-interface=lo",
        f"dhcp-leasefile={_DNSMASQ_LEASES_FILE}",
        f"dhcp-range={net.dhcp_hosts[0]},{net.dhcp_hosts[-1]},1h",
        f"dhcp-option=option:dns-server,{net.host_address}",
        "dhcp-option=option:domain-name",
        "log-queries",
        "log-dhcp",
        "log-debug",
        f"pid-file={_DNSMASQ_PID_FILE}",
        f"addn-hosts={_DNSMASQ_HOSTS_FILE}",
    ]

    conf_lines.extend(_render_koe_abitti_net_dns_lines())

    try:
        user = os.environ["SUDO_USER"]
    except KeyError:
        # Let dnsmasq switch uid to it's default, normally nobody
        pass
    else:
        # Ensure no tricks are being played, that the user actually exists.
        user = subprocess.check_output(["id", "-un", user], timeout=2).decode().strip()
        conf_lines.append(f"user={user}")

    with open(_DNSMASQ_CONF_FILE, "w", encoding="utf-8") as dnsmasq_conf_file:
        for conf_line in conf_lines:
            print(conf_line, file=dnsmasq_conf_file)

    args = ["dnsmasq", f"--conf-file={_DNSMASQ_CONF_FILE}"]
    _LOGGER.info(
        "Spawning dnsmasq with conf file %s: %s", _DNSMASQ_CONF_FILE, conf_lines
    )
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
