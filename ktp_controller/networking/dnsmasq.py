# Standard library imports
import logging
import os
import subprocess
import time

# Third-party imports
import validators

# Internal imports
import ktp_controller.net

_THIS_NAME = "ktp-controller-networking"
_LOGGER = logging.getLogger(__name__)
_PID_FILE = f"/run/{_THIS_NAME}-dnsmasq.pid"
_LEASES_FILE = f"/var/lib/{_THIS_NAME}-dnsmasq.leases"
HOSTS_FILE = f"/var/lib/{_THIS_NAME}-dnsmasq.hosts"
_CONF_FILE = f"/var/lib/{_THIS_NAME}-dnsmasq.conf"
LOCAL_DOMAIN = "koe.abitti.net"


KOE_ABITTI_NET_DNS_SERVERS = [
    "9.9.9.9",
    "1.1.1.1",
    "8.8.8.8",
]


def render_koe_abitti_net_dns_lines() -> list[str]:
    lines = [
        f"server=/{LOCAL_DOMAIN}/{koe_abitti_net_dns_server}"
        for koe_abitti_net_dns_server in KOE_ABITTI_NET_DNS_SERVERS
    ]
    if len(KOE_ABITTI_NET_DNS_SERVERS) > 0:
        lines.append("all-servers")
    return lines


def render_ipset_lines(
    *, allowed_wan_domains: list[str], ipset_name: str | None
) -> list[str]:
    if ipset_name is None:
        return []

    if len(allowed_wan_domains) == 0:
        return []

    for d in allowed_wan_domains:
        if not validators.domain(d):
            raise ValueError("invalid domain", d)

    return [f"ipset=/{'/'.join(allowed_wan_domains)}/{ipset_name}"]


def start_dhcp_dns_server(
    net: ktp_controller.net.Net,
    *,
    allowed_wan_domains: list[str],
    ipset_name: str | None,
    local_dns_ttl: int,
) -> int:
    conf_lines = [
        "port=53",
        f"listen-address={net.host_address}",
        f"local-ttl={local_dns_ttl}",
        "dhcp-ttl=0",
        f"domain={LOCAL_DOMAIN},{net.network}",
        "domain-needed",
        "bogus-priv",
        "no-hosts",
        "bind-interfaces",
        "except-interface=lo",
        f"dhcp-leasefile={_LEASES_FILE}",
        f"dhcp-range={net.dhcp_hosts[0]},{net.dhcp_hosts[-1]},1h",
        f"dhcp-option=option:dns-server,{net.host_address}",
        "dhcp-option=option:domain-name",
        "log-queries",
        "log-dhcp",
        "log-debug",
        f"pid-file={_PID_FILE}",
        f"addn-hosts={HOSTS_FILE}",
    ]

    conf_lines.extend(render_koe_abitti_net_dns_lines())
    conf_lines.extend(
        render_ipset_lines(
            allowed_wan_domains=allowed_wan_domains,
            ipset_name=ipset_name,
        )
    )

    try:
        user = os.environ["SUDO_USER"]
    except KeyError:
        # Let dnsmasq switch uid to it's default, normally nobody
        pass
    else:
        # Ensure no tricks are being played, that the user actually exists.
        user = subprocess.check_output(["id", "-un", user], timeout=2).decode().strip()
        conf_lines.append(f"user={user}")

    with open(_CONF_FILE, "w", encoding="utf-8") as dnsmasq_conf_file:
        for conf_line in conf_lines:
            print(conf_line, file=dnsmasq_conf_file)

    args = ["dnsmasq", f"--conf-file={_CONF_FILE}"]
    _LOGGER.info("Spawning dnsmasq with conf file %s: %s", _CONF_FILE, conf_lines)
    subprocess.check_call(args)

    return 0


def kill_dnsmasq(sig: int) -> bool:
    with open(_PID_FILE, encoding="ascii") as dnsmasq_pid_file:
        dnsmasq_pid = int(dnsmasq_pid_file.read().strip())

    try:
        os.kill(dnsmasq_pid, sig)
    except ProcessLookupError:
        os.unlink(_PID_FILE)
        return True

    return False


def stop_dhcp_dns_server() -> int:
    # First gently.
    if kill_dnsmasq(15):
        return 0

    # Give it some time to die.
    for _ in range(4):
        time.sleep(0.5)
        if kill_dnsmasq(0):
            return 0

    # Then with force.
    if kill_dnsmasq(9):
        _LOGGER.error("failed to kill dnsmasq gracefully!")
        return 1

    _LOGGER.critical("failed to kill dnsmasq!")
    return 1
