# Standard library imports
import logging
import os
import subprocess

# Internal imports
import ktp_controller.networking.dnsmasq as dnsmasq

_LOGGER = logging.getLogger(__name__)
_NM_CONF_FILE = "/etc/NetworkManager/dnsmasq.d/puavo-ers.conf"


def reload_networkmanager() -> None:
    completed_process = subprocess.run(
        ["systemctl", "reload", "NetworkManager.service"],
        capture_output=True,
    )
    if completed_process.returncode != 0:
        _LOGGER.warning(
            "failed to reload NetworkManager: %s", completed_process.stderr.decode()
        )


def configure_nm_dnsmasq_plugin() -> None:
    """Best-effort inclusion of the domain record in the local DNS controlled by NetworkManager"""
    try:
        with open(f"{_NM_CONF_FILE}.tmp", "w", encoding="utf-8") as nm_conf_file:
            print(f"address=/{dnsmasq.LOCAL_DOMAIN}/::", file=nm_conf_file)
            print(f"addn-hosts={dnsmasq.DNSMASQ_HOSTS_FILE}", file=nm_conf_file)
            for line in dnsmasq.render_koe_abitti_net_dns_lines():
                print(line, file=nm_conf_file)
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

    reload_networkmanager()


def unconfigure_nm_dnsmasq_plugin() -> None:
    try:
        os.unlink(_NM_CONF_FILE)
    except FileNotFoundError:
        return  # A bit weird situation, but that's ok.

    reload_networkmanager()
